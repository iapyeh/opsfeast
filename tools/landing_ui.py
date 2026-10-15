"""Local overview, author defaults and navigation to the recipes workbench."""
import asyncio
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
AUTHOR_LABELS = {'name': 'Recipe Author', 'contacts': 'Author Contact Info', 'license': 'Default Recipe License'}
UNCONFIGURED = 'Not configured — click to set'

DOCUMENTS = {
    'README.md': 'Overview', 'docs/first-use.md': 'First use',
    'docs/first-host.md': 'First host', 'docs/terminal-ui.md': 'Terminal interface',
    'docs/cli.md': 'CLI reference',
}


def overview():
    from checkout_info import information
    info = information()
    return f'OpsFeast {info["version"]}\nDownloaded: {info["downloaded_at"]}'



def document(name):
    if name not in DOCUMENTS:
        raise ValueError('unsupported help document')
    return (ROOT / name).read_text(encoding='utf-8')


def make_home_class():
    from rich.text import Text
    from textual.binding import Binding
    from textual.containers import Container, Vertical, VerticalScroll
    from textual.screen import ModalScreen
    from textual.widgets import Input
    import json
    import recipe_identity
    from textual.widgets import Button, DataTable, Markdown, RichLog, Select, Static, TabbedContent, TabPane, Tabs, Tree
    from recipe_workbench import make_workbench_class
    Workbench = make_workbench_class()

    class AuthorInput(ModalScreen):
        DEFAULT_CSS = """
        AuthorInput { align: center middle; }
        AuthorInput > Vertical { width: 90%; max-width: 80; height: auto; padding: 1 2; background: $surface; }
        AuthorInput Static { height: auto; }
        """
        BINDINGS = [Binding('escape', 'cancel', 'Cancel', priority=True)]
        def __init__(self, field, value):
            super().__init__()
            self.field = field
            self.value = json.dumps(value, ensure_ascii=False) if field == 'contacts' else value
        def compose(self):
            with Vertical():
                yield Static('Edit ' + AUTHOR_LABELS[self.field], markup=False)
                if self.field == 'contacts':
                    yield Static('Contacts: JSON list, e.g. ["name@example.org", "https://example.org"]', markup=False)
                yield Input(value=self.value, id='author-value')
                yield Static('', id='author-error', markup=False)
                yield Button('Save', id='save-author', variant='primary')
                yield Button('Cancel', id='cancel-author')
        def on_mount(self):
            self.query_one(Input).focus()
        def action_cancel(self):
            self.dismiss(False)
        def submit(self):
            value = self.query_one(Input).value.strip()
            try:
                if self.field == 'contacts':
                    value = json.loads(value)
                recipe_identity.save_field(self.field, value)
            except json.JSONDecodeError:
                self.query_one('#author-error', Static).update('Contacts must be a JSON list of nonempty strings.')
            except Exception as exc:
                from opsfeast import ConfigError
                message = str(exc) if isinstance(exc, ConfigError) else type(exc).__name__
                self.query_one('#author-error', Static).update('Save failed: ' + message)
            else:
                self.dismiss(True)
        def on_input_submitted(self, event):
            self.submit()
        def on_button_pressed(self, event):
            event.stop()
            if event.button.id == 'save-author':
                self.submit()
            elif event.button.id == 'cancel-author':
                self.action_cancel()

    class Home(Workbench):
        TITLE = 'OpsFeast'
        INITIAL_PANE = 'home-pane'
        SECTION_IDS = ('home-pane', 'profiles-pane', 'output-pane', 'hosts-pane', 'help-pane', 'actions-pane')
        CUSTOM_RECIPE_PANE = True
        BINDINGS = [Binding('enter', 'host_menu', 'Host actions', show=False, priority=True), Binding('f1', 'show_help', 'Help', priority=True),
                    Binding('down', 'management_down', show=False, priority=True),
                    Binding('up', 'management_up', show=False, priority=True)]
        CSS = Workbench.CSS + '\n#product-info { padding: 1 2; height: auto; } #author-controls { height: auto; padding: 0 2; } #author-controls Static { height: auto; } #author-heading { text-style: bold; } #author-context { margin-bottom: 1; } #author-controls Button { width: 100%; height: 3; } #author-status { height: auto; } #hosts-status, #profiles-status { height: auto; } #hosts-body { height: 1fr; } #host-list { dock: left; width: 30%; min-width: 18; max-width: 36; height: 100%; border-right: solid $primary; } #host-details { height: 1fr; } #profile-list { height: 1fr; }'
        def __init__(self):
            super().__init__()
            self.host_entries = {}
            self.host_root = None
            self.host_selection_node = None
            self.profile_entries = {}
            self.management_busy = False
            self.host_operation_busy = False
        def landing_panes(self):
            with TabPane('Home', id='home-pane'):
                yield Static(overview(), id='product-info', markup=False)
                with Vertical(id='author-controls'):
                    yield Static('Defaults for New Recipes', id='author-heading', markup=False)
                    yield Static('Used when creating your own recipes. Existing recipes are not changed.', id='author-context', markup=False)
                    for field, label in AUTHOR_LABELS.items():
                        yield Button(Text(label + ': ' + UNCONFIGURED), id='author-' + field)
                    yield Static('', id='author-status', markup=False)
            with TabPane('Profiles', id='profiles-pane'):
                yield Static('Reading profiles…', id='profiles-status', markup=False)
                yield DataTable(id='profile-list', cursor_type='row')
                yield Button('Switch selected profile', id='switch-profile', variant='primary')
            yield from self.recipe_pane()
            with TabPane('Hosts', id='hosts-pane'):
                yield Static('Reading current profile…', id='hosts-status', markup=False)
                yield Button('Refresh hosts / profiles', id='refresh-management')
                with Container(id='hosts-body'):
                    yield Tree('Hosts', id='host-list')
                    yield RichLog(id='host-details', wrap=True, markup=False, auto_scroll=False)
            with TabPane('Help', id='help-pane'):
                yield Select([(title, name) for name, title in DOCUMENTS.items()], value='README.md', allow_blank=False, id='help-document')
                with VerticalScroll():
                    yield Markdown('', id='help-text', open_links=False)
        def after_mount(self):
            self.refresh_author_controls()
            self.query_one('#host-list', Tree).show_root = False
            self.query_one('#profile-list', DataTable).add_columns('Profile', 'Root', 'Status', 'Default')
            self.run_worker(self.refresh_management(), exclusive=True, group='management', exit_on_error=False)
            self.call_after_refresh(self.focus_home)
        def refresh_author_controls(self):
            try:
                identity = recipe_identity.defaults()
                status = ''
            except Exception as exc:
                identity = recipe_identity.normalized({})
                status = 'Author defaults unavailable: ' + type(exc).__name__
            for field, label in AUTHOR_LABELS.items():
                value = identity['license'] if field == 'license' else identity['author'][field]
                missing = value == ['Unknown'] if field == 'contacts' else value == 'Unknown'
                display = UNCONFIGURED if missing else (', '.join(value) if field == 'contacts' else value)
                self.query_one('#author-' + field, Button).label = Text(label + ': ' + display)
            self.query_one('#author-status', Static).update(status)
        def edit_author(self, field):
            try:
                identity = recipe_identity.defaults()
            except Exception as exc:
                self.query_one('#author-status', Static).update('Author defaults unavailable: ' + type(exc).__name__ + '; repair the local configuration file first.')
                return
            value = identity['license'] if field == 'license' else identity['author'][field]
            def finished(saved):
                self.refresh_author_controls()
                self.call_after_refresh(self.query_one('#author-' + field, Button).focus)
            self.push_screen(AuthorInput(field, value), finished)
        def focus_home(self):
            self.focus_section_tabs('home-pane')
        def on_tabbed_content_tab_activated(self, event):
            if event.tabbed_content.id == 'workbench-tabs' and event.pane.id == 'hosts-pane':
                self.call_after_refresh(self.restore_host_cursor)
        def restore_host_cursor(self):
            if self.query_one('#workbench-tabs', TabbedContent).active == 'hosts-pane' and self.host_selection_node is not None:
                tree = self.query_one('#host-list', Tree)
                if tree.cursor_node is not None and tree.cursor_node.data is not None:
                    self.host_selection_node = tree.cursor_node
                else:
                    tree.move_cursor(self.host_selection_node)
        def check_action(self, action, parameters):
            if action == 'host_menu':
                tree = self.query_one('#host-list', Tree)
                return tree.screen is self.screen and self.focused is tree and tree.cursor_node is not None and self.node_host(tree.cursor_node.data) in self.host_entries
            if action in {'management_down', 'management_up'}:
                tabs = self.query_one('#workbench-tabs', TabbedContent)
                return (tabs.screen is self.screen and tabs.active in {'hosts-pane', 'profiles-pane', 'output-pane'}
                        and (self.focused is tabs.query_one(Tabs) or isinstance(self.focused, Button)))
            return super().check_action(action, parameters)
        def move_management_row(self, down):
            pane = self.query_one('#workbench-tabs', TabbedContent).active
            table = self.query_one('#host-list', Tree) if pane == 'hosts-pane' else (self.query_one('#recipe-tree', Tree) if pane == 'output-pane' else self.query_one('#profile-list', DataTable))
            self.screen.set_focus(table)
            if down:
                table.action_cursor_down()
            else:
                table.action_cursor_up()
        def action_management_down(self):
            self.move_management_row(True)
        def action_management_up(self):
            self.move_management_row(False)
        async def refresh_management(self):
            from management_view import hosts_snapshot, profiles_snapshot
            profiles, hosts = await asyncio.to_thread(lambda: (profiles_snapshot(), hosts_snapshot()))
            self.render_management(profiles, hosts)
        def render_management(self, profiles, hosts):
            self.profile_entries = {row['name']: row for row in profiles['profiles']}
            self.host_entries = {row['host']: row for row in hosts['hosts']}
            self.host_root = hosts.get('root')
            table = self.query_one('#profile-list', DataTable)
            table.clear()
            for name, row in self.profile_entries.items():
                table.add_row(Text(name), Text(row['root']), Text(row['status']), Text('*' if row['default'] else ''), key=name)
            for index, row in enumerate(self.profile_entries.values()):
                if row['default']:
                    table.move_cursor(row=index)
                    break
            from management_view import grouped_hosts, user_accounts
            tree = self.query_one('#host-list', Tree)
            previous = tree.cursor_node.data if tree.cursor_node else None
            tree.clear()
            tree.root.expand()
            leaves = []
            for group, names in grouped_hosts(hosts['hosts']).items():
                group_label = group if group is not None else 'Ungrouped (no group)'
                branch = tree.root.add(Text(group_label), expand=True)
                for name in names:
                    settings = self.host_entries[name]['settings']
                    host_node = branch.add(Text(settings.get('icon', '🍎') + ' ' + name), data=name, expand=True)
                    leaves.append(host_node)
                    login, accounts = user_accounts(self.host_entries[name]['settings'])
                    for user in accounts:
                        fallback = hosts.get('user_icons', {}).get(user, self.host_entries[name].get(
                            'default_user_icon', hosts.get('default_user_icon', '👤')))
                        icon = settings.get('users', {}).get(user, {}).get('icon', fallback)
                        leaves.append(host_node.add_leaf(Text(icon + ' ' + user + (' (login)' if user == login else '')), data=('user', name, user)))
            selected = next((node for node in leaves if node.data == previous), leaves[0] if leaves else None)
            self.host_selection_node = selected
            if selected is not None:
                tree.move_cursor(selected)
                self.call_after_refresh(self.restore_host_cursor)
            self.query_one('#profiles-status', Static).update(Text(profiles['message']))
            self.query_one('#hosts-status', Static).update(Text(f'Profile: {hosts.get("profile") or "none"}\n{hosts["message"]}'))
            self.show_host(selected.data if selected is not None else None)
        def node_host(self, data):
            return data[1] if isinstance(data, tuple) and len(data) == 3 and data[0] == 'user' else data
        def show_host(self, key):
            import json
            log = self.query_one('#host-details', RichLog)
            log.clear()
            host = self.node_host(key)
            if host in self.host_entries:
                row = self.host_entries[host]
                if isinstance(key, tuple):
                    user = key[2]
                    row = {'host': host, 'user': user, 'source': row['source'],
                           'settings': row['settings'].get('users', {}).get(user, {})}
                log.write(Text(json.dumps(row, ensure_ascii=False, indent=2, default=str)))
        def on_tree_node_highlighted(self, event):
            if event.control.id == 'host-list':
                if event.node.data is not None:
                    self.host_selection_node = event.node
                self.show_host(event.node.data)
                if event.node.data is None:
                    self.query_one('#host-details', RichLog).write(Text('Group: ' + event.node.label.plain + '\nSelect a host ID to inspect its settings.'))
        def on_tree_node_selected(self, event):
            if event.control.id == 'host-list' and event.node.data is not None:
                self.show_host(event.node.data)
        def action_host_menu(self):
            if not self.done or self.management_busy or self.host_operation_busy:
                self.notify('Wait for the active operation to finish.', severity='warning')
                return
            from host_actions import dialog_classes, command_for
            HostMenu, RecipeInput, Operation = dialog_classes()
            tree = self.query_one('#host-list', Tree)
            data = tree.cursor_node.data
            host = self.node_host(data)
            user = data[2] if isinstance(data, tuple) else None
            from management_view import user_accounts
            login, _ = user_accounts(self.host_entries[host]['settings'])
            root = self.host_root
            if not root:
                self.notify('No valid Feast directory is available.', severity='warning')
                return
            def closed(result=None):
                self.host_operation_busy = False
                if result is not None:
                    self.run_worker(self.refresh_browser(), exclusive=True, group='browser', exit_on_error=False)
                self.call_after_refresh(lambda: self.screen.set_focus(tree) if tree.screen is self.screen else None)
            def run(action, recipe=''):
                self.host_operation_busy = True
                self.push_screen(Operation(command_for(action, host, root, recipe, user=user), host, root, user=user), closed)
            def chosen(action):
                if action in {'test-connection', 'test-su', 'test-sudo'}: run(action)
                elif action == 'run recipe':
                    self.push_screen(RecipeInput(host, root), lambda path: run(action, path) if path else closed())
                else: closed()
            self.push_screen(HostMenu(host, root, user=user, login=login), chosen)
        def on_data_table_row_highlighted(self, event):
            event.prevent_default()
            if event.data_table.id == 'profile-list':
                event.stop()
            else:
                super().on_data_table_row_highlighted(event)
        def on_data_table_row_selected(self, event):
            event.prevent_default()
            if event.data_table.id == 'profile-list':
                self.request_profile_switch(event.row_key.value)
            else:
                super().on_data_table_row_selected(event)
        def request_profile_switch(self, name=None):
            table = self.query_one('#profile-list', DataTable)
            if name is None and table.row_count:
                name = table.ordered_rows[table.cursor_row].key.value
            row = self.profile_entries.get(name)
            if not self.done or self.management_busy or self.host_operation_busy:
                self.notify('Wait for the active operation to finish.', severity='warning')
            elif not row or row['status'] != 'available':
                self.notify('Select an available profile.', severity='warning')
            else:
                self.management_busy = True
                self.run_worker(self.switch_profile(name), exclusive=True, group='management', exit_on_error=False)
        async def switch_profile(self, name):
            from opsfeast import set_default_profile
            try:
                await asyncio.to_thread(set_default_profile, name)
                await self.refresh_management()
                await self.refresh_browser()
                self.query_one('#profiles-status', Static).update(Text('Default profile switched to ' + name + '. Hosts refreshed; explicit recipe environment preserved.'))
            except Exception as exc:
                self.query_one('#profiles-status', Static).update(Text('Profile switch failed: ' + type(exc).__name__))
            finally:
                self.management_busy = False
        def action_close_result(self):
            if self.management_busy or self.host_operation_busy:
                self.notify('An operation is still active.', severity='warning')
            else:
                super().action_close_result()
        def action_show_help(self):
            tabs = self.query_one('#workbench-tabs', TabbedContent)
            if tabs.screen is self.screen:
                self.query_one('#help-document', Select).value = 'docs/first-use.md'
                self.activate_section('help-pane')
        def on_button_pressed(self, event):
            key = event.button.id
            if key in {'author-name', 'author-contacts', 'author-license'}:
                event.stop()
                self.edit_author(key.removeprefix('author-'))
            elif key == 'switch-profile':
                self.request_profile_switch()
            elif key == 'refresh-management':
                if not self.management_busy:
                    self.run_worker(self.refresh_management(), exclusive=True, group='management', exit_on_error=False)
            elif key == 'apply' and self.management_busy:
                self.notify('An operation is still active.', severity='warning')
                event.prevent_default()
        async def on_select_changed(self, event):
            if event.select.id == 'help-document' and event.value in DOCUMENTS:
                try:
                    text = document(event.value)
                except (OSError, ValueError):
                    text = 'This help document is unavailable. Consult the checkout documentation.'
                await self.query_one('#help-text', Markdown).update(text)

    return Home


def launch():
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print('ERROR: OpsFeast home requires a terminal; use --help or an explicit CLI subcommand.', file=sys.stderr)
        return 2
    try:
        app = make_home_class()()
    except ImportError:
        print('ERROR: OpsFeast home requires Textual; install requirements-tui.txt.', file=sys.stderr)
        return 1
    try:
        app.run()
    except Exception as exc:
        print(f'ERROR: home display failed ({type(exc).__name__}); review saved results and cleanup evidence.', file=sys.stderr)
        return 1
    return 0
