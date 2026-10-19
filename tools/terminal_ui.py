"""Optional Textual presentation of an unchanged CLI invocation."""
import asyncio
from collections import Counter
import json
import os
from pathlib import Path
import sys
import time
from display_time import human_times

from terminal_events import decode


def child_arguments(script, argv):
    """Remove only the UI flag; never reinterpret targets or invocation inputs."""
    if argv.count('--tui') != 1:
        raise ValueError('specify --tui exactly once')
    args = [arg for arg in argv if arg != '--tui']
    if script.name == 'opsfeast.py':
        allowed = {'check', 'inspect-recipe', 'test-connection', 'host-init', 'test-host', 'test-su', 'test-sudo'}
        recipe_allowed = len(args) > 1 and args[:1] == ['recipes'] and args[1] in {'list', 'show', 'results', 'run'}
        if not args or (args[0] not in allowed and not recipe_allowed):
            raise ValueError('--tui supports check, inspect-recipe, diagnostics and recipes list/show/results/run')
        if args[0] == 'inspect-recipe' or recipe_allowed and args[1] in {'list', 'show', 'results'}:
            if '--json' not in args:
                args.append('--json')
        elif args[0] in allowed - {'check'} and not any(flag in args for flag in ('--verbose', '-v', '--quiet', '-q')):
            args.append('--verbose')
    elif script.name != 'run_recipe.py':
        raise ValueError('unsupported TUI entrypoint')
    if script.name == 'run_recipe.py' or args[:2] == ['recipes', 'run']:
        if not any(flag in args for flag in ('--quiet', '-q', '--verbose', '-v')):
            args.append('--verbose')
    return args


def _report_rows(report):
    """Keep reported states verbatim; connection-only booleans are explicit."""
    if not isinstance(report, dict):
        return []
    if isinstance(report.get('hosts'), list):
        return [(str(item.get('host', index)), item) for index, item in enumerate(report['hosts']) if isinstance(item, dict)]
    if isinstance(report.get('tests'), dict):
        return [(str(name), item) for name, item in report['tests'].items() if isinstance(item, dict)]
    if isinstance(report.get('groups'), list):
        return [(' / '.join(map(str, item.get('accounts', []))) or str(index), item)
                for index, item in enumerate(report['groups']) if isinstance(item, dict)]
    for field in ('recipes', 'results'):
        if isinstance(report.get(field), list):
            return [(str(item.get('reference') or item.get('result_id') or
                         (item.get('descriptor') or {}).get('id') or item.get('directory') or index), item)
                    for index, item in enumerate(report[field]) if isinstance(item, dict)]
    return [(str(report.get('host', report.get('host_id', report.get('recipe_id', 'Result')))), report)]


def report_rows(report):
    rows, used = [], set()
    for label, item in _report_rows(report):
        key, count = label, 1
        while key in used:
            count += 1
            key = f'{label} [{count}]'
        used.add(key)
        rows.append((key, item))
    return rows


def reported_status(item):
    if 'status' in item:
        return str(item['status'])
    if isinstance(item.get('success'), bool):
        return 'success' if item['success'] else 'failed'
    if isinstance(item.get('runnable'), bool):
        return 'compatible' if item['runnable'] else 'unavailable'
    return 'unknown'


def make_app_class():
    # Lazy import keeps every ordinary command usable without Textual.
    from rich.text import Text
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.widgets import DataTable, Footer, Header, RichLog, Static, TabbedContent, TabPane

    class TerminalApp(App):
        TITLE = 'OpsFeast'
        CSS = '''
        #summary { height: auto; padding: 0 1; }
        #table { height: 40%; min-height: 5; }
        TabbedContent { height: 1fr; }
        RichLog { height: 1fr; }
        '''
        BINDINGS = [Binding('q', 'close_result', 'Close when finished'),
                    Binding('ctrl+q', 'close_result', show=False, priority=True),
                    Binding('ctrl+c', 'close_result', 'Close when finished', priority=True)]

        def __init__(self, command, diagnostic_host=None):
            super().__init__()
            self.command = command
            self.diagnostic_host = diagnostic_host
            self.done = False
            self.process = None
            self.exit_status = 1
            self.items = {}
            self.started = {}
            self.output = ''
            self.began = time.monotonic()

        def compose(self) -> ComposeResult:
            yield Header()
            yield Static('Starting…', id='summary', markup=False)
            yield DataTable(id='table', cursor_type='row')
            with TabbedContent():
                with TabPane('Details', id='details-pane'):
                    yield RichLog(id='details', wrap=True, markup=False, highlight=False, auto_scroll=False)
                with TabPane('Progress / errors', id='log-pane'):
                    yield RichLog(id='log', wrap=True, markup=False, highlight=False, max_lines=2000)
                with TabPane('Original output', id='raw-pane'):
                    yield RichLog(id='raw', wrap=True, markup=False, highlight=False, auto_scroll=False)
            yield Footer()

        def on_mount(self):
            self.query_one('#table', DataTable).add_columns('Host / test / recipe', 'Status', 'Stage / reason', 'Elapsed', 'Retention', 'Content', 'Result path')
            self.set_interval(1, self.refresh_elapsed)
            self.run_worker(self.collect(), exit_on_error=False)

        def update_item(self, key, item):
            table = self.query_one('#table', DataTable)
            old = self.items.get(key, {})
            item = dict(old, **item)
            self.items[key] = item
            self.started.setdefault(key, time.monotonic())
            retention = item.get('retention') or {}
            retention_status = retention.get('status', '—') if isinstance(retention, dict) else 'unknown'
            content = item.get('content_update') or {}
            content_status = content.get('status', '—') if isinstance(content, dict) else 'unknown'
            status = reported_status(item)
            style = {'success': 'green', 'failed': 'red', 'partial': 'yellow', 'skipped': 'yellow', 'unsupported': 'yellow'}.get(status, '')
            elapsed = item.setdefault('_elapsed', None)
            elapsed = elapsed if elapsed is not None else time.monotonic() - self.started[key]
            cells = (Text(key), Text(status, style=style), Text(str(item.get('reason_code', item.get('stage', '')))),
                     Text(f'{elapsed:.0f}s'), Text(str(retention_status)), Text(str(content_status)), Text(str(item.get('result_path') or '—')))
            if key in table.rows:
                for column, cell in zip(table.columns, cells):
                    table.update_cell(key, column, cell)
            else:
                table.add_row(*cells, key=key)

        def refresh_elapsed(self):
            if not self.done:
                for key, item in list(self.items.items()):
                    if item.get('_elapsed') is None:
                        self.update_item(key, {})

        def event(self, event):
            kind = event['kind']
            if kind == 'selected':
                for host in event.get('hosts', []):
                    self.update_item(str(host), {'status': 'pending'})
            elif kind in {'stage', 'result'}:
                key = event.get('host') or self.diagnostic_host
                if key:
                    item = {k: v for k, v in event.items() if k not in {'kind', 'host'}}
                    if kind == 'stage':
                        item['status'] = 'running'
                    else:
                        item['_elapsed'] = time.monotonic() - self.started.get(str(key), time.monotonic())
                    self.update_item(str(key), item)
                if kind == 'stage':
                    self.query_one('#summary', Static).update(Text(str(event.get('stage', 'Running…'))))

        async def collect(self):
            try:
                env = dict(os.environ, OPSFEAST_TUI_EVENTS='1', PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1')
                self.process = await asyncio.create_subprocess_exec(*self.command, stdin=asyncio.subprocess.DEVNULL,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env)
                async def errors():
                    while line := await self.process.stderr.readline():
                        value = line.decode('utf-8', errors='replace').rstrip('\r\n')
                        event = decode(value)
                        if event is not None:
                            self.event(event)
                        else:
                            self.query_one('#log', RichLog).write(Text(value))
                async def output():
                    chunks = []
                    while chunk := await self.process.stdout.read(65536):
                        chunks.append(chunk)
                    self.output = b''.join(chunks).decode('utf-8', errors='replace')
                await asyncio.gather(errors(), output())
                self.exit_status = await self.process.wait()
                self.finish(self.output, self.exit_status)
            except Exception as exc:
                self.query_one('#log', RichLog).write(Text(f'Display failure: {type(exc).__name__}'))
                self.exit_status = 1
                self.done = True
                self.query_one('#summary', Static).update('Display failed; see Progress / errors.')
            finally:
                if self.process is not None and self.process.returncode is None:
                    self.process.terminate()
                    await self.process.wait()

        def finish(self, output, code):
            self.output, self.exit_status, self.done = output, code, True
            self.query_one('#raw', RichLog).write(Text(output or '(No stdout; see Progress / errors.)'))
            try:
                report = json.loads(output)
            except ValueError:
                report = None
            rows = report_rows(report)
            # Replace live host rows with the final diagnostic test/group rows.
            if rows:
                self.query_one('#table', DataTable).clear()
                previous = self.items
                self.items = {}
                for key, item in rows:
                    elapsed = previous.get(key, {}).get('_elapsed')
                    if elapsed is None:
                        elapsed = time.monotonic() - self.started.get(key, self.began)
                    self.update_item(key, dict(item, _elapsed=elapsed))
            else:
                for key in list(self.items):
                    if self.items[key].get('_elapsed') is None:
                        self.update_item(key, {'status': 'unknown', 'reason_code': 'no_final_result',
                                               '_elapsed': time.monotonic() - self.started[key]})
            counts = Counter(reported_status(item) for item in self.items.values())
            summary = ', '.join(f'{status}: {count}' for status, count in counts.items()) or 'Text output'
            if isinstance(report, dict) and report.get('excluded_hosts'):
                summary += f"; excluded: {len(report['excluded_hosts'])}"
            self.query_one('#summary', Static).update(Text(f'Finished — exit {code} | {summary} | {time.monotonic() - self.began:.0f}s. Select a row; q to close.'))
            self.show_details(next(iter(self.items), None))

        def show_details(self, key):
            detail = self.query_one('#details', RichLog)
            detail.clear()
            if key in self.items:
                item = {k: v for k, v in self.items[key].items() if not k.startswith('_')}
                detail.write(Text(json.dumps(human_times(item), indent=2, ensure_ascii=False)))

        def on_data_table_row_highlighted(self, event):
            self.show_details(event.row_key.value)

        def action_close_result(self):
            if self.done:
                self.exit(self.exit_status)
            else:
                self.notify('Execution is still active. Close is available after completion.', severity='warning')

        def action_quit(self):
            self.action_close_result()

    return TerminalApp


def launch(script, argv):
    try:
        args = child_arguments(script, argv)
    except ValueError as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print('ERROR: --tui requires terminal stdin/stdout; omit --tui for JSON, pipes or automation.', file=sys.stderr)
        return 2
    try:
        app_class = make_app_class()
    except ImportError:
        print('ERROR: --tui requires Textual; install requirements-tui.txt in this interpreter.', file=sys.stderr)
        return 1
    host = args[1] if script.name == 'opsfeast.py' and args[0] in {'test-connection', 'host-init', 'test-host', 'test-su', 'test-sudo'} and len(args) > 1 else None
    app = app_class([sys.executable, '-B', str(script.resolve()), *args], host)
    try:
        app.run()
    except Exception as exc:
        print(f'ERROR: terminal display failed ({type(exc).__name__}); review saved results and cleanup evidence.', file=sys.stderr)
        return 1
    return app.exit_status
