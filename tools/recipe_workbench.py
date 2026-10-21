"""Recipes workbench: explicit forms dispatch to the shared recipes CLI."""
import json
from pathlib import Path
import sys

from terminal_ui import make_app_class

ACTIONS = {
    'list': ('Browse recipes', ('query', 'kind', 'html')),
    'show': ('Inspect recipe', ('recipe',)),
    'run': ('Run recipe / report', ('recipe', 'hosts', 'groups', 'all', 'exclude', 'variables', 'vars_file', 'inputs', 'threads', 'timeout')),
    'results-list': ('Browse report results', ('recipe_id', 'status', 'html')),
    'results-show': ('Inspect report result', ('result_id', 'html')),
    'artifact': ('Verify artifact', ('result_id', 'name')),
    'jobs-list': ('List saved jobs', ()),
    'jobs-show': ('Inspect saved job', ('name',)),
    'jobs-save': ('Save invocation as job', ('name', 'recipe', 'hosts', 'groups', 'all', 'exclude', 'variables', 'vars_file', 'inputs', 'threads', 'timeout')),
    'jobs-run': ('Run saved job', ('name',)),
    'pack': ('Pack recipe bundle', ('recipe', 'files', 'output')),
    'unpack': ('Unpack review candidate', ('archive', 'destination')),
}
LABELS = {
    'recipe': 'Recipe reference', 'hosts': 'Hosts — JSON array of exact IDs',
    'groups': 'Groups — JSON array of exact names', 'all': 'All enabled hosts — true / false',
    'exclude': 'Excluded hosts — JSON array (requires all)', 'variables': 'Variables — JSON object',
    'inputs': 'Report input files — JSON array', 'files': 'Bundle file allowlist — JSON array',
    'vars_file': 'Variables JSON file', 'threads': 'Host concurrency', 'timeout': 'Per-stage timeout (seconds)',
    'query': 'Catalog search', 'kind': 'Kind — operation / report', 'html': 'New HTML output path (optional)',
    'recipe_id': 'Recipe ID filter', 'host': 'Host ID filter', 'status': 'Result status filter',
    'result_id': 'Storage-relative result ID', 'name': 'Job / artifact name',
    'output': 'New bundle ZIP path', 'archive': 'Bundle ZIP to review', 'destination': 'New candidate directory',
}


def arguments(action, scope, location, fields):
    """Build argv, never a shell command; do not guess missing targets."""
    if action not in ACTIONS or scope not in {'checkout', 'default', 'profile', 'root'}:
        raise ValueError('select a valid action and environment')
    args = action.split('-')
    values = {key: fields.get(key, '').strip() for key in ACTIONS[action][1]}
    required = {'show': ('recipe',), 'run': ('recipe',), 'results-show': ('result_id',),
                'artifact': ('result_id', 'name'), 'jobs-show': ('name',), 'jobs-save': ('name', 'recipe'),
                'jobs-run': ('name',), 'pack': ('recipe', 'output', 'files'), 'unpack': ('archive', 'destination')}
    for key in required.get(action, ()):
        if not values.get(key):
            raise ValueError(f'{LABELS[key]} is required')
    positional = {'show': ('recipe',), 'run': ('recipe',), 'results-show': ('result_id',),
                  'artifact': ('result_id', 'name'), 'jobs-show': ('name',), 'jobs-save': ('name', 'recipe'),
                  'jobs-run': ('name',), 'pack': ('recipe',), 'unpack': ('archive',)}
    for key in positional.get(action, ()):
        if values[key].startswith('-'):
            raise ValueError(f'{LABELS[key]} cannot start with a dash')
        args.append(values[key])
    if action != 'unpack':
        if scope == 'checkout':
            if action not in {'list', 'show', 'pack'}:
                raise ValueError('This action requires a Feast: choose default, profile or root.')
            args.append('--checkout-only')
        elif scope in {'root', 'profile'}:
            if not location.strip():
                raise ValueError('Environment path or profile name is required')
            args.extend(['--' + scope, location.strip()])
    for key, value in values.items():
        if not value or key in positional.get(action, ()):
            continue
        if key in {'hosts', 'groups', 'exclude', 'inputs', 'files'}:
            items = json.loads(value)
            if not isinstance(items, list) or any(not isinstance(item, str) or not item or item.startswith('-') for item in items):
                raise ValueError(f'{LABELS[key]} must contain nonempty strings without leading dashes')
            option = {'hosts': 'host', 'groups': 'group', 'exclude': 'exclude', 'inputs': 'input', 'files': 'file'}[key]
            if key == 'exclude':
                if items: args.extend(['--exclude', *items])
                continue
            for item in items:
                args.extend(['--' + option, item])
        elif key == 'variables':
            variables = json.loads(value)
            if not isinstance(variables, dict):
                raise ValueError('Variables must be a JSON object')
            for name, item in variables.items():
                if not name or '=' in name or name.startswith('-'):
                    raise ValueError('Invalid variable name')
                literal = item if isinstance(item, str) else json.dumps(item, allow_nan=False)
                args.extend(['--var', name + '=' + literal])
        elif key == 'all':
            if value not in {'true', 'false'}:
                raise ValueError('All must be true or false')
            if value == 'true': args.append('--all')
        else:
            args.append('--' + key.replace('_', '-') + '=' + value)
    if action in {'list', 'show', 'results-list'}:
        args.append('--json')
    if action in {'run', 'jobs-save'}:
        args.append('--verbose')
    return args


def needs_confirmation(action, fields):
    return action in {'run', 'jobs-save', 'jobs-run', 'pack', 'unpack'} or bool(fields.get('html', '').strip())


def make_workbench_class():
    from rich.text import Text
    from textual.app import ComposeResult
    from textual.binding import Binding
    from textual.containers import Container, Horizontal, VerticalScroll
    from textual.screen import ModalScreen
    from textual.widgets import Button, DataTable, Footer, Header, Input, Label, RichLog, Select, Static, TabbedContent, TabPane, Tabs, Tree
    Base = make_app_class()

    class Review(ModalScreen):
        DEFAULT_CSS = 'Review { align: center middle; } Review > VerticalScroll { width: 90%; height: 85%; background: $surface; padding: 1 2; }'
        def __init__(self, args):
            super().__init__()
            self.args = args
        def compose(self):
            with VerticalScroll():
                yield Label('Review execution / write scope')
                yield Static(Text('CLI arguments:\n' + json.dumps(['recipes', *self.args], ensure_ascii=False, indent=2)))
                yield Static('Review the recipe, targets, variables and file destinations. This uses the existing CLI checks; it is not a sandbox.', markup=False)
                yield Button('Confirm and execute', id='confirm', variant='warning')
                yield Button('Cancel', id='cancel')
        def on_button_pressed(self, event):
            self.dismiss(event.button.id == 'confirm')

    class Workbench(Base):
        TITLE = 'OpsFeast Recipes'
        INITIAL_PANE = 'output-pane'
        SECTION_IDS = ('output-pane', 'actions-pane')
        CUSTOM_RECIPE_PANE = False
        BINDINGS = [Binding('ctrl+tab', 'next_section', 'Next tab', priority=True),
                    Binding('ctrl+shift+tab', 'previous_section', 'Previous tab', priority=True),
                    Binding('escape', 'focus_parent', 'Back focus', priority=True),
                    Binding('down', 'recipe_down', show=False, priority=True),
                    Binding('up', 'recipe_up', show=False, priority=True)]
        CSS = Base.CSS + '\n#form { padding: 1 2; } #form Input { margin-bottom: 1; } #workbench-tabs { height: 1fr; } #form-status { height: auto; } #browser-status, #history-status { height: auto; } #recipe-browser-body { height: 1fr; } #recipe-tree { dock: left; width: 30%; min-width: 18; max-width: 36; height: 100%; border-right: solid $primary; } #recipe-history { height: 40%; min-height: 5; } #execution-status { height: auto; }'
        def __init__(self):
            super().__init__([])
            self.done = True
            self.browser_data = None
            self.recipe_entries = {}
            self.execution_rows = {}
            self.execution_token = 0
        def compose(self) -> ComposeResult:
            yield Header()
            with TabbedContent(id='workbench-tabs', initial=self.INITIAL_PANE):
                yield from self.landing_panes()
                if not self.CUSTOM_RECIPE_PANE:
                    yield from self.recipe_pane()
                with TabPane('Actions', id='actions-pane'):
                    with TabbedContent(id='action-view'):
                        with TabPane('Configure', id='action-config-pane'):
                            with VerticalScroll(id='form'):
                                yield Label('Action')
                                yield Select([(title, key) for key, (title, _) in ACTIONS.items()], value='list', allow_blank=False, id='action')
                                yield Label('Environment (opening uses checkout only)')
                                yield Select([('Checkout only', 'checkout'), ('Default Feast', 'default'), ('Named profile', 'profile'), ('Feast directory', 'root')], value='checkout', allow_blank=False, id='scope')
                                yield Label('Profile name / absolute Feast directory')
                                yield Input(id='location')
                                for key, label in LABELS.items():
                                    yield Label(label, id='label-' + key)
                                    yield Input(id='field-' + key)
                                yield Static('', id='form-status', markup=False)
                                with Horizontal():
                                    yield Button('Apply / review action', id='apply', variant='primary')
                        with TabPane('Output', id='action-output-pane'):
                            yield Static('Reading checkout catalog…', id='summary', markup=False)
                            yield DataTable(id='table', cursor_type='row')
                            with TabbedContent():
                                with TabPane('Details'):
                                    yield RichLog(id='details', wrap=True, markup=False, auto_scroll=False)
                                with TabPane('Progress / errors'):
                                    yield RichLog(id='log', wrap=True, markup=False, max_lines=2000)
                                with TabPane('Original output'):
                                    yield RichLog(id='raw', wrap=True, markup=False, auto_scroll=False)
            yield Footer()
        def recipe_pane(self):
            with TabPane('Recipes', id='output-pane'):
                yield Static('Reading recipe sources…', id='browser-status', markup=False)
                yield Button('Refresh recipes / history', id='refresh-browser')
                with Container(id='recipe-browser-body'):
                    yield Tree('Recipe sources', id='recipe-tree')
                    with TabbedContent(id='recipe-view'):
                        with TabPane('Info', id='info-pane'):
                            yield RichLog(id='recipe-info', wrap=True, markup=False, highlight=False, auto_scroll=False)
                        with TabPane('Executions', id='history-pane'):
                            yield Static('Select a recipe directory.', id='history-status', markup=False)
                            yield DataTable(id='recipe-history', cursor_type='row')
                            yield Static('Select an execution to inspect its saved result.', id='execution-status', markup=False)
                            with TabbedContent(id='execution-view'):
                                with TabPane('Details', id='execution-details-pane'):
                                    yield RichLog(id='execution-details', wrap=True, markup=False, highlight=False, auto_scroll=False)
                                with TabPane('Original output', id='execution-original-pane'):
                                    yield RichLog(id='execution-original', wrap=True, markup=False, highlight=False, auto_scroll=False)
        async def refresh_browser(self):
            import asyncio
            from recipe_browser import snapshot, directory_parts, source_label
            data = await asyncio.to_thread(snapshot)
            self.browser_data = data
            tree = self.query_one('#recipe-tree', Tree)
            previous = tree.cursor_node.data if tree.cursor_node else None
            tree.clear()
            tree.root.expand()
            self.recipe_entries = {}
            first = selected = None
            for source in data['catalog']['sources']:
                if source['name'] == 'profile' and not any(item['source'] == 'profile' for item in data['catalog']['recipes']):
                    continue
                node = tree.root.add(Text(source_label(source, data.get('profile_name'))), expand=True)
                paths = {(): node}
                for item in data['catalog']['recipes']:
                    if item['source'] != source['name']: continue
                    parts = directory_parts(item, source)
                    for index in range(1, len(parts) + 1):
                        prefix = parts[:index]
                        if prefix not in paths:
                            paths[prefix] = paths[prefix[:-1]].add(Text(prefix[-1]), expand=True)
                    leaf = paths[parts]
                    leaf.data = item['reference']
                    self.recipe_entries[item['reference']] = item
                    if first is None: first = leaf
                    if leaf.data == previous: selected = leaf
            selected = selected or first
            self.browser_selection = selected
            self.query_one('#browser-status', Static).update(Text(data['message']))
            if selected is not None:
                self.show_recipe_history(selected.data)
                self.call_after_refresh(self.restore_recipe_cursor)
            else:
                self.show_recipe_history(None)
                self.query_one('#history-status', Static).update('No recipes available; inspect source status.')
        def restore_recipe_cursor(self):
            if self.query_one('#workbench-tabs', TabbedContent).active == 'output-pane' and getattr(self, 'browser_selection', None) is not None:
                tree = self.query_one('#recipe-tree', Tree)
                if tree.cursor_node is not None and tree.cursor_node.data in self.recipe_entries:
                    self.browser_selection = tree.cursor_node
                else:
                    tree.move_cursor(self.browser_selection)
        def show_recipe_history(self, reference):
            from recipe_browser import history_for, describe, display_started, started_column
            table = self.query_one('#recipe-history', DataTable)
            table.clear(columns=True)
            self.execution_rows = {}
            self.execution_token += 1
            self.clear_execution()
            item = self.recipe_entries.get(reference)
            rows = history_for(item, self.browser_data['history']['results']) if item is not None else []
            table.add_columns(started_column(row.get('started_at') for row in rows), 'Status', 'Host (--host)', 'Result ID')
            info = self.query_one('#recipe-info', RichLog)
            info.clear()
            info.write(Text(describe(item)))
            if item is None:
                self.query_one('#history-status', Static).update('Select a recipe directory to inspect its execution history.')
                return
            for row in rows:
                self.execution_rows[row['result_id']] = (item, row)
                host = row.get('host_id') or ('(offline report)' if row.get('kind') == 'report' else '(unknown)')
                table.add_row(Text(display_started(row.get('started_at'))), Text(str(row['status'])), Text(str(host)), Text(row['result_id']), key=row['result_id'])
            missing = sum(not r.get('recipe_reference') or not r.get('recipe_source') for r in self.browser_data['history']['results'])
            errors = len(self.browser_data['history'].get('errors', []))
            self.query_one('#history-status', Static).update(Text(f'{reference}: {len(rows)} run(s) | Invalid: {errors} | Unattributed: {missing}'))
        def clear_execution(self):
            for name in ('execution-details', 'execution-original'):
                self.query_one('#' + name, RichLog).clear()
            self.query_one('#execution-status', Static).update('Select an execution to inspect its saved result.')
        def on_data_table_row_highlighted(self, event):
            event.prevent_default()
            if event.data_table.id == 'recipe-history':
                self.request_execution(event.row_key.value)
            else:
                super().on_data_table_row_highlighted(event)
        def on_data_table_row_selected(self, event):
            event.prevent_default()
            if event.data_table.id == 'recipe-history':
                self.request_execution(event.row_key.value)
        def request_execution(self, identifier):
            entry = self.execution_rows.get(identifier)
            if entry is None:
                return
            self.execution_token += 1
            token = self.execution_token
            self.clear_execution()
            self.query_one('#execution-status', Static).update(Text('Reading saved result: ' + identifier))
            self.run_worker(self.read_execution(token, identifier, entry[0], self.browser_data['root']),
                            exclusive=True, group='execution', exit_on_error=False)
        async def read_execution(self, token, identifier, item, root):
            import asyncio
            from recipe_browser import execution_output
            try:
                output = await asyncio.to_thread(execution_output, root, identifier, item)
            except Exception as exc:
                if token == self.execution_token:
                    self.query_one('#execution-status', Static).update(Text('Saved result unavailable: ' + type(exc).__name__ + ' — refresh history or inspect the result file.'))
                return
            if token != self.execution_token:
                return
            for name, key in (('execution-details', 'details'), ('execution-original', 'original')):
                self.query_one('#' + name, RichLog).write(Text(output[key]))
            self.query_one('#execution-status', Static).update(Text('Saved result: ' + identifier))
        def on_tree_node_highlighted(self, event):
            if event.control.id == 'recipe-tree':
                if event.node.data in self.recipe_entries:
                    self.browser_selection = event.node
                self.show_recipe_history(event.node.data)
        def on_mount(self, event):
            event.prevent_default()
            self.query_one('#table', DataTable).add_columns('Host / test / recipe', 'Status', 'Stage / reason', 'Elapsed', 'Retention', 'Result path')
            self.query_one('#recipe-tree', Tree).show_root = False
            self.run_worker(self.refresh_browser(), exclusive=True, group='browser', exit_on_error=False)
            self.set_interval(1, self.refresh_elapsed)
            self.show_fields('list')
            self.start(['list', '--checkout-only', '--json'])
            self.after_mount()
        def landing_panes(self):
            return iter(())
        def check_action(self, action, parameters):
            if action == 'focus_parent':
                tabs = self.query_one('#workbench-tabs', TabbedContent)
                if tabs.screen is not self.screen:
                    return False
                # An open Select must consume Escape to close its dropdown.
                if self.focused is not None:
                    for widget in [self.focused, *self.focused.ancestors]:
                        if isinstance(widget, Select) and widget.expanded:
                            return False
                return True
            if action in {'recipe_down', 'recipe_up'}:
                tabs = self.query_one('#workbench-tabs', TabbedContent)
                return (tabs.screen is self.screen and tabs.active == 'output-pane'
                        and (self.focused is tabs.query_one(Tabs) or isinstance(self.focused, Button)))
            return super().check_action(action, parameters)
        def action_focus_parent(self):
            tabs = self.query_one('#workbench-tabs', TabbedContent)
            if tabs.screen is not self.screen:
                return
            top = tabs.query_one(Tabs)
            focused = self.focused
            if focused is top:
                return
            sidebar = content = None
            if tabs.active == 'output-pane':
                sidebar = self.query_one('#recipe-tree', Tree)
                content = self.query_one('#recipe-view', TabbedContent)
            elif tabs.active == 'hosts-pane':
                sidebar = self.query_one('#host-list', Tree)
                content = self.query_one('#host-details', RichLog)
            in_content = focused is not None and content is not None and (focused is content or content in focused.ancestors)
            self.screen.set_focus(sidebar if in_content else top)
        def move_recipe_cursor(self, down):
            tree = self.query_one('#recipe-tree', Tree)
            self.screen.set_focus(tree)
            if down: tree.action_cursor_down()
            else: tree.action_cursor_up()
        def action_recipe_down(self): self.move_recipe_cursor(True)
        def action_recipe_up(self): self.move_recipe_cursor(False)
        def after_mount(self):
            pass
        def switch_section(self, step):
            tabs = self.query_one('#workbench-tabs', TabbedContent)
            if tabs.screen is self.screen:
                index = self.SECTION_IDS.index(tabs.active)
                self.activate_section(self.SECTION_IDS[(index + step) % len(self.SECTION_IDS)])
        def activate_section(self, pane):
            tabs = self.query_one('#workbench-tabs', TabbedContent)
            if tabs.screen is self.screen:
                # Hiding a focused pane otherwise focuses another child in that
                # pane, whose Focused message reactivates the old tab.
                self.screen.set_focus(None)
                tabs.active = pane
                if pane != 'output-pane':
                    self.call_after_refresh(self.focus_section_tabs, pane)
        def focus_section_tabs(self, pane):
            tabs = self.query_one('#workbench-tabs', TabbedContent)
            if tabs.active == pane and tabs.screen is self.screen:
                self.screen.set_focus(tabs.query_one(Tabs))
        def action_next_section(self):
            self.switch_section(1)
        def action_previous_section(self):
            self.switch_section(-1)
        def show_fields(self, action):
            fields = ACTIONS[action][1]
            for key in LABELS:
                self.query_one('#label-' + key).display = key in fields
                self.query_one('#field-' + key).display = key in fields
        def on_select_changed(self, event):
            if event.select.id == 'action' and event.value in ACTIONS:
                self.show_fields(event.value)
        def on_tabbed_content_tab_activated(self, event):
            if event.tabbed_content.id == 'workbench-tabs' and event.pane.id == 'output-pane':
                self.call_after_refresh(self.restore_recipe_cursor)
                self.call_after_refresh(self.focus_recipe_browser)
        def focus_recipe_browser(self):
            focused = self.focused
            content = self.query_one('#recipe-view', TabbedContent)
            if focused is self.query_one('#recipe-tree', Tree) or (focused is not None and (focused is content or content in focused.ancestors)):
                # A delayed tab-activation callback must not steal focus after
                # the user has already entered the sidebar or content.
                return
            self.focus_section_tabs('output-pane')
        def focus_results(self):
            table = self.query_one('#table', DataTable)
            if self.query_one('#workbench-tabs', TabbedContent).active == 'actions-pane' and table.screen is self.screen:
                self.screen.set_focus(table)
        def start(self, args):
            import time
            self.items, self.started, self.output = {}, {}, ''
            self.began = time.monotonic()
            self.done, self.exit_status = False, 1
            self.query_one('#table', DataTable).clear()
            for key in ('details', 'log', 'raw'):
                self.query_one('#' + key, RichLog).clear()
            self.query_one('#summary', Static).update('Running selected action…')
            self.command = [sys.executable, '-B', str(Path(__file__).with_name('opsfeast.py')), 'recipes', *args]
            self.run_worker(self.collect(), exit_on_error=False)
            if self.query_one('#action-view', TabbedContent).active == 'action-output-pane':
                self.call_after_refresh(self.focus_results)
        def on_button_pressed(self, event):
            if event.button.id == 'refresh-browser':
                self.run_worker(self.refresh_browser(), exclusive=True, group='browser', exit_on_error=False)
                return
            if event.button.id != 'apply': return
            if not self.done:
                self.notify('An action is still running.', severity='warning')
                return
            action = self.query_one('#action', Select).value
            fields = {key: self.query_one('#field-' + key, Input).value for key in ACTIONS[action][1]}
            try:
                args = arguments(action, self.query_one('#scope', Select).value, self.query_one('#location', Input).value, fields)
            except (ValueError, TypeError) as exc:
                self.query_one('#form-status', Static).update(Text(str(exc)))
                return
            self.query_one('#form-status', Static).update('')
            def proceed(confirmed=True):
                if confirmed and self.done:
                    self.activate_section('actions-pane')
                    self.query_one('#action-view', TabbedContent).active = 'action-output-pane'
                    self.start(args)
            if needs_confirmation(action, fields): self.push_screen(Review(args), proceed)
            else: proceed()
        def finish(self, output, code):
            super().finish(output, code)
            if self.command[-3:] != ['list', '--checkout-only', '--json']:
                self.run_worker(self.refresh_browser(), exclusive=True, group='browser', exit_on_error=False)

    return Workbench


def launch():
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print('ERROR: recipes workbench requires a terminal; use recipes list/show/run or --help.', file=sys.stderr)
        return 2
    try:
        app = make_workbench_class()()
    except ImportError:
        print('ERROR: recipes workbench requires Textual; install requirements-tui.txt.', file=sys.stderr)
        return 1
    try:
        app.run()
    except Exception as exc:
        print(f'ERROR: workbench failed ({type(exc).__name__}); review saved results and cleanup evidence.', file=sys.stderr)
        return 1
    return 0
