"""Host-bound modal actions over existing diagnostic/recipe CLI entrypoints."""
import asyncio
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def command_for(action, host, root, recipe='', user=None):
    if not host or not root:
        raise ValueError('host and Feast directory are required')
    if action == 'test-connection':
        return [sys.executable, '-B', str(ROOT/'tools/opsfeast.py'), 'test-connection', host, root, '--verbose']
    if action in {'test-su', 'test-sudo'}:
        from host_runtime import username
        user = username(user)
        args = [sys.executable, '-B', str(ROOT/'tools/opsfeast.py'), action, host, user, '--root='+root, '--verbose']
        if action == 'test-sudo': args.append('--run-as=root')
        return args
    if action == 'run recipe' and recipe.strip():
        return [sys.executable, '-B', str(ROOT/'tools/opsfeast.py'), 'recipes', 'run', recipe.strip(), '--host', host, '--root='+root, '--verbose']
    raise ValueError('select a valid operation and nonempty recipe path')


async def execute(command, progress, log):
    from terminal_events import decode
    process = None
    try:
        process = await asyncio.create_subprocess_exec(*command, stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            env=dict(os.environ, OPSFEAST_TUI_EVENTS='1', PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1'))
        async def errors():
            while line := await process.stderr.readline():
                value = line.decode('utf-8', errors='replace').rstrip('\r\n')
                event = decode(value)
                if event is not None:
                    if event.get('kind') == 'stage': progress(str(event.get('stage', 'Running…')))
                else: log(value)
        async def output():
            chunks = []
            while chunk := await process.stdout.read(65536): chunks.append(chunk)
            return b''.join(chunks).decode('utf-8', errors='replace')
        _, result = await asyncio.gather(errors(), output())
        return await process.wait(), result
    finally:
        if process is not None and process.returncode is None:
            process.terminate()
            await process.wait()


def dialog_classes():
    from rich.text import Text
    from textual.binding import Binding
    from textual.containers import Vertical
    from textual.screen import ModalScreen
    from textual.widgets import Button, Input, ProgressBar, RichLog, SelectionList, Static

    class Dialog(ModalScreen):
        DEFAULT_CSS = 'Dialog { align: center middle; } Dialog > Vertical { width: 90%; height: 80%; background: $surface; padding: 1 2; } Dialog Static { height: auto; } Dialog SelectionList { height: 6; } Dialog RichLog { height: 1fr; }'
        BINDINGS = [Binding('escape', 'cancel', 'Cancel', priority=True), Binding('q', 'cancel', show=False)]
        def action_cancel(self): self.dismiss(None)

    class HostMenu(Dialog):
        def __init__(self, host, root, user=None, login=None):
            super().__init__()
            self.host, self.root = host, root
            self.user, self.login = user, login
        def compose(self):
            with Vertical():
                yield Static(Text(f'Host: {self.host}\nFeast: {self.root}\nChoose one action (Enter or Space).'))
                options = ['test-connection', 'run recipe', 'cancel']
                if self.user is not None:
                    yield Static(Text(f'User: {self.user} | Login: {self.login or "unknown (test-su unavailable)"}'))
                    options = (['test-su'] if self.login is not None and self.user != self.login else []) + ['test-sudo', 'cancel']
                yield SelectionList(*[(option, option) for option in options], id='host-actions')
        def on_mount(self): self.query_one(SelectionList).focus()
        def on_selection_list_selection_toggled(self, event):
            value = event.selection.value
            self.dismiss(None if value == 'cancel' else value)

    class RecipeInput(Dialog):
        def __init__(self, host, root):
            super().__init__()
            self.host, self.root = host, root
        def compose(self):
            with Vertical():
                yield Static(Text(f'Run recipe on {self.host}\nFeast: {self.root}\nEnter a reviewed operational recipe path.'))
                yield Input(placeholder='system/inventory/overview or ./recipes/custom', id='recipe-path')
                yield Static('', id='input-error', markup=False)
                yield Button('Run on this host', id='run', variant='warning')
                yield Button('Cancel', id='cancel')
        def on_mount(self): self.query_one(Input).focus()
        def submit(self):
            value = self.query_one(Input).value.strip()
            if not value:
                self.query_one('#input-error', Static).update('Recipe path is required.')
            else: self.dismiss(value)
        def on_input_submitted(self, event): self.submit()
        def on_button_pressed(self, event):
            if event.button.id == 'run': self.submit()
            else: self.dismiss(None)

    class Operation(Dialog):
        def __init__(self, command, host, root, user=None):
            super().__init__()
            self.command, self.host, self.root = command, host, root
            self.user = user
            self.done = False
            self.exit_code = None
        def compose(self):
            with Vertical():
                yield Static(Text(f'Host: {self.host}\nFeast: {self.root}' + (f'\nUser: {self.user}' if self.user else '')))
                yield Static('Starting…', id='operation-stage', markup=False)
                yield ProgressBar(total=None, show_percentage=False, show_eta=False, id='operation-progress')
                yield RichLog(id='operation-result', wrap=True, markup=False, max_lines=3000, auto_scroll=False)
                yield Button('Close', id='close', disabled=True)
        def on_mount(self): self.run_worker(self.run_operation(), exit_on_error=False)
        async def run_operation(self):
            stage = self.query_one('#operation-stage', Static)
            log = self.query_one('#operation-result', RichLog)
            try:
                code, output = await execute(self.command, lambda message: stage.update(Text(message)), lambda message: log.write(Text(message)))
                self.exit_code = code
                try:
                    result = json.dumps(json.loads(output), indent=2, ensure_ascii=False)
                except ValueError: result = output
                log.write(Text('\nResult:\n' + (result or '(No stdout; inspect errors above.)')))
                stage.update(Text(f'Finished — exit {code}. Review result/cleanup/retention states below.'))
            except Exception as exc:
                self.exit_code = 1
                stage.update(Text('Operation/display failed: ' + type(exc).__name__ + '. Review saved results and cleanup evidence.'))
            finally:
                self.done = True
                self.query_one(ProgressBar).update(total=1, progress=1)
                self.query_one('#close', Button).disabled = False
        def action_cancel(self):
            if self.done: self.dismiss(self.exit_code)
            else: self.notify('Operation is active; wait for completion.', severity='warning')
        def on_button_pressed(self, event): self.action_cancel()

    return HostMenu, RecipeInput, Operation
