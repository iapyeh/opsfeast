"""Host icon loading contract; all YAML/instances are temporary and synthetic."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import yaml
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opsfeast import ConfigError, Instance, Validator, main
from management_view import hosts_snapshot


class HostIconTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.entry = self.root / 'hosts.yaml'

    def write(self, **fields):
        self.entry.write_text(json.dumps({'hosts': {'h': dict(connection={'local': True}, **fields)}}, ensure_ascii=False), errors='backslashreplace')

    def load(self):
        validator = Validator(self.root)
        validator.load(self.entry)
        return validator

    def test_default_is_visible_without_modifying_yaml_or_raw_document(self):
        self.entry.write_text('# Human note\nhosts:\n  h:\n    connection: {local: true}\n')
        original = self.entry.read_bytes()
        validator = self.load()
        self.assertEqual(validator.hosts['h']['icon'], '🍎')
        self.assertNotIn('icon', validator.documents[self.entry]['hosts']['h'])
        validator.check_connections()
        self.assertEqual(self.entry.read_bytes(), original)

    def test_explicit_single_symbols_preserved(self):
        for icon in ('🍎', '🐧', '★', '☀', '$', '+', '©'):
            with self.subTest(icon=icon):
                self.write(icon=icon)
                self.assertEqual(self.load().check_connections().hosts['h']['icon'], icon)

    def test_invalid_type_character_count_or_category_rejected_on_load(self):
        for icon in (None, '', '🍎🍎', 'A', 'é', '1', ' ', '\n', '\x00', '\ud800', '\ufe0f',
                     '☀️', '👍🏽', '🇹🇼', '👩\u200d💻', 1, True, [], {}):
            with self.subTest(icon=repr(icon)):
                self.write(icon=icon)
                with self.assertRaisesRegex(ConfigError, 'h.icon: expected exactly one Unicode Symbol code point'):
                    self.load()

    def test_include_default_and_override_are_independent(self):
        self.entry.write_text('include: [extra.yaml]\nhosts:\n  first:\n    connection: {local: true}\n')
        (self.root / 'extra.yaml').write_text('hosts:\n  second:\n    icon: 🐧\n    connection: {local: true}\n')
        hosts = self.load().hosts
        self.assertEqual({key: host['icon'] for key, host in hosts.items()}, {'first': '🍎', 'second': '🐧'})

    def test_global_precedence_includes_users_and_raw_documents(self):
        self.entry.write_text("""default:
  icon:
    user: ★
    host: 🐧
include: [extra.yaml]
hosts:
  explicit:
    icon: ☀
    group: team
    connection: {local: true}
    users: {alice: {icon: ♠}, bob: {sudo: false}}
  plain:
    connection: {local: true}
groups:
  team: {icon: {host: ♣}}
""")
        (self.root / 'extra.yaml').write_text('hosts:\n  grouped:\n    group: [team, ops]\n    connection: {local: true}\n    users: {carol: {}}\n')
        original = self.entry.read_bytes()
        v = self.load().check_connections()
        self.assertEqual({name: h['icon'] for name, h in v.hosts.items()},
                         {'grouped': '♣', 'explicit': '☀', 'plain': '🐧'})
        self.assertEqual(v.hosts['explicit']['users']['alice']['icon'], '♠')
        self.assertEqual(v.hosts['explicit']['users']['bob']['icon'], '★')
        self.assertEqual(v.hosts['grouped']['users']['carol']['icon'], '★')
        self.assertNotIn('icon', v.documents[self.entry]['hosts']['explicit']['users']['bob'])
        self.assertEqual(self.entry.read_bytes(), original)
        from console_output import DisplayIcons, user_label, diagnostic
        from access_check import host_summary, format_summary
        icons = DisplayIcons(v)
        self.assertEqual(user_label('undeclared', 'plain', icons), '★ undeclared')
        self.assertEqual(user_label('alice', 'explicit', icons), '♠ alice')
        self.assertIn('♠ alice', diagnostic({'host': 'explicit', 'status': 'success'}, 'su', icons, 'alice'))
        self.assertIn('♠ alice', host_summary({'host': 'explicit', 'status': 'success', 'user': 'alice'}, icons))
        report = {'hosts': [{'host': 'explicit', 'status': 'success', 'user': 'alice',
                            'access': {}}], 'counts': {'success': 1, 'failed': 0, 'skipped': 0}}
        self.assertIn('♠ alice', format_summary(report, icons))

    def test_builtin_user_and_group_without_configured_group_default(self):
        self.write(group='team', users={'alice': {}})
        v = self.load().check_connections()
        self.assertEqual(v.hosts['h']['icon'], '🍎')
        self.assertEqual(v.hosts['h']['users']['alice']['icon'], '👤')
        self.assertNotIn('icon', v.documents[self.entry]['hosts']['h']['users']['alice'])

    def test_invalid_global_and_user_icons_and_include_defaults(self):
        for field in ('user', 'host', 'groups', 'users'):
            for invalid in (None, '', 'text', '☀️', False):
                if field == 'groups':
                    default = {'groups': {'team': {'icon': {'host': invalid}}}}
                elif field == 'users':
                    default = {'users': {'alice': {'icon': invalid}}}
                else:
                    default = {'icon': {field: invalid}}
                payload = {'default': default, 'hosts': {}}
                if field == 'groups':
                    payload['groups'] = payload['default'].pop('groups')
                self.entry.write_text(json.dumps(payload))
                with self.subTest(field=field, invalid=invalid), self.assertRaises(ConfigError):
                    self.load()
        self.entry.write_text('include: [extra.yaml]\n')
        (self.root / 'extra.yaml').write_text('default: {icon: {host: ★}}\n')
        with self.assertRaises(ConfigError):
            self.load()
        for invalid in (None, '', 'text', '☀️', False):
            self.write(users={'alice': {'icon': invalid}})
            with self.subTest(user_icon=invalid), self.assertRaisesRegex(ConfigError, 'users.alice.icon'):
                self.load()


    def test_per_group_host_and_user_precedence_are_independent(self):
        data = {'default': {'icon': {'user': '★', 'host': '☀'}, 'groups': {
            'web-server': {'icon': {'user': '👨', 'host': '🖥'}},
            'backup-server': {'icon': {'host': '🗂'}},
            'users-only': {'icon': {'user': '♣'}}}}, 'hosts': {}}
        data['groups'] = data['default'].pop('groups')
        cases = {
            'web': (['web-server'], '🖥', '👨'),
            'backup': (['backup-server'], '🗂', '★'),
            'ordered': (['backup-server', 'web-server'], '🗂', '👨'),
            'reversed': (['web-server', 'backup-server'], '🖥', '👨'),
            'independent': (['users-only', 'backup-server'], '🗂', '♣'),
            'unknown': (['unknown'], '☀', '★'),
            'ungrouped': ([], '☀', '★'),
        }
        for name, (groups, _, _) in cases.items():
            data['hosts'][name] = {'connection': {'local': True}, 'group': groups,
                                   'users': {'alice': {}, 'bob': {'icon': '♠'}}}
        self.entry.write_text(json.dumps(data, ensure_ascii=False))
        v = self.load().check_connections()
        from console_output import DisplayIcons, user_label
        icons = DisplayIcons(v)
        for name, (_, host_icon, user_icon) in cases.items():
            with self.subTest(host=name):
                self.assertEqual(v.hosts[name]['icon'], host_icon)
                self.assertEqual(v.hosts[name]['users']['alice']['icon'], user_icon)
                self.assertEqual(v.hosts[name]['users']['bob']['icon'], '♠')
                self.assertEqual(user_label('implicit-login', name, icons), f'{user_icon} implicit-login')
        # Core snapshots receive the same effective values through the shared loader.
        profile = Instance.open(self.root).profile(root=self.root)
        self.assertEqual(profile.hosts.get('ordered')['users']['alice']['icon'], '👨')

    def test_invalid_nested_structure_unknown_fields_and_old_names_rejected(self):
        for value in (None, False, [], '★', {'typo': {}}, {'icon': None},
                      {'icon': {'typo': '★'}}, {'icon': {'group': {}}}, {'icon': {'users': None}}, {'icon': {'groups': None}},
                      {'icon': {'groups': {'team': '★'}}},
                      {'icon': {'groups': {'team': {'icon': '★'}}}}):
            self.entry.write_text(json.dumps({'default': value}))
            with self.subTest(default=value), self.assertRaises(ConfigError):
                self.load()
        for old in ('default-user-icon', 'default-host-icon', 'default-group-icon'):
            self.entry.write_text(json.dumps({old: '★'}))
            with self.assertRaises(ConfigError):
                self.load()

    def test_named_user_defaults_override_groups_and_preserve_explicit_icons(self):
        self.entry.write_text("""default:
  icon:
    user: 👤
  users:
    alice: {icon: 👩}
    implicit-login: {icon: ★}
include: [extra.yaml]
hosts:
  h:
    group: [backup-server, web-server]
    connection: {hostname: fixture, user: implicit-login}
    users: {alice: {}, bob: {}, explicit: {icon: ♠}}
  ungrouped:
    connection: {local: true}
    users: {alice: {}, bob: {}}
groups:
  web-server: {icon: {host: 🖥, user: 👨}}
  backup-server: {icon: {host: 🗂}}
""")
        (self.root / 'extra.yaml').write_text('hosts:\n  included:\n    group: web-server\n    connection: {local: true}\n    users: {alice: {icon: ♣}}\n')
        original = self.entry.read_bytes()
        v = self.load().check_connections()
        self.assertEqual(v.hosts['h']['users']['alice']['icon'], '👩')
        self.assertEqual(v.hosts['h']['users']['bob']['icon'], '👨')
        self.assertEqual(v.hosts['h']['users']['explicit']['icon'], '♠')
        self.assertEqual(v.hosts['ungrouped']['users']['alice']['icon'], '👩')
        self.assertEqual(v.hosts['ungrouped']['users']['bob']['icon'], '👤')
        self.assertEqual(v.hosts['included']['users']['alice']['icon'], '♣')
        self.assertNotIn('icon', v.documents[self.entry]['hosts']['h']['users']['alice'])
        self.assertNotIn('implicit-login', v.hosts['h']['users'])
        self.assertEqual(self.entry.read_bytes(), original)
        from console_output import DisplayIcons, user_label, diagnostic
        from access_check import host_summary
        icons = DisplayIcons(v)
        self.assertEqual(user_label('implicit-login', 'h', icons), '★ implicit-login')
        self.assertEqual(user_label('alice', 'h', icons), '👩 alice')
        self.assertEqual(user_label('alice', 'included', icons), '♣ alice')
        self.assertIn('★ implicit-login', diagnostic({'host': 'h', 'status': 'success'}, 'connection', icons, 'implicit-login'))
        self.assertIn('★ implicit-login', host_summary({'host': 'h', 'status': 'success', 'user': 'implicit-login'}, icons))
        profile = Instance.open(self.root).profile(root=self.root)
        self.assertEqual(profile.hosts.get('h')['users']['alice']['icon'], '👩')
        import opsfeast
        with patch.object(opsfeast, 'resolve_root', return_value=self.root), \
                patch.object(opsfeast, 'load_profiles', return_value={'default_profile': 'main'}):
            snapshot = hosts_snapshot()
        self.assertEqual(snapshot['user_icons']['implicit-login'], '★')
        self.assertEqual(next(h for h in snapshot['hosts'] if h['host'] == 'h')['default_user_icon'], '👨')

    def test_named_user_defaults_validate_every_entry(self):
        for users in ([], '★', {'alice': '★'}, {'alice': {'icon': '☀️'}}, {'alice': False},
                      {'': {'icon': '★'}}, {1: {'icon': '★'}}, {'alice': {'email': None}},
                      {'alice': {'email': 1}}, {'alice': {'email': 'x\x00y'}}, {'alice': {'typo': '★'}}):
            self.entry.write_text(yaml.safe_dump({'default': {'users': users}}, allow_unicode=True))
            with self.subTest(users=users), self.assertRaises(ConfigError):
                self.load()

    def test_metadata_only_user_and_empty_defaults_preserve_fallbacks(self):
        self.entry.write_text("""default:
  users:
    alice: {email: alice@example.org}
    bob: {}
hosts:
  h:
    group: [empty, web]
    connection: {local: true}
    users: {alice: {}, bob: {}}
groups:
  web: {icon: {user: 👩}}
  empty: {}
""")
        v = self.load().check_connections()
        self.assertEqual(v.hosts['h']['icon'], '🍎')
        self.assertEqual(v.hosts['h']['users']['alice']['icon'], '👩')
        self.assertEqual(v.hosts['h']['users']['bob']['icon'], '👩')
        self.assertNotIn('email', v.hosts['h']['users']['alice'])
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(['dump', 'default.users.alice', str(self.root)]), 0)
        self.assertEqual(json.loads(output.getvalue()), {'email': 'alice@example.org'})

    def test_new_group_shapes_and_defaults_in_includes_are_validated(self):
        for groups in (None, [], {'web': None}, {'web': {'host': '★'}},
                       {'web': {'icon': None}}, {'web': {'icon': {'user': False}}},
                       {'web': {'icon': {'host': '★'}, 'email': 'team@example.org'}}):
            self.entry.write_text(yaml.safe_dump({'groups': groups}))
            with self.subTest(groups=groups), self.assertRaises(ConfigError):
                self.load()
        for defaults in ({'groups': {}}, {'users': {}}):
            self.entry.write_text('include: [extra.yaml]\n')
            (self.root / 'extra.yaml').write_text(yaml.safe_dump({'default': defaults}))
            with self.assertRaises(ConfigError):
                self.load()

    def test_core_reload_inspection_and_failed_reload_preserve_snapshot(self):
        self.write()
        profile = Instance.open(self.root).profile(root=self.root)
        self.assertEqual(profile.hosts.get('h')['icon'], '🍎')
        self.write(icon='🐧')
        self.assertEqual(profile.inspect()['hosts']['h']['icon'], '🐧')
        self.assertEqual(profile.hosts.get('h')['icon'], '🍎')
        profile.reload()
        self.assertEqual(profile.hosts.get('h', reveal_secrets=True)['icon'], '🐧')
        self.write(icon='☀️')
        with self.assertRaises(ConfigError):
            profile.reload()
        self.assertEqual(profile.hosts.get('h')['icon'], '🐧')

    def test_cli_dump_and_ui_read_model_receive_effective_default(self):
        self.write()
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(['dump', 'hosts.h.icon', str(self.root)])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue()), '🍎')
        import opsfeast
        with patch.object(opsfeast, 'resolve_root', return_value=self.root), \
                patch.object(opsfeast, 'load_profiles', return_value={'default_profile': 'main'}):
            self.assertEqual(hosts_snapshot()['hosts'][0]['settings']['icon'], '🍎')
        self.write(icon='invalid')
        error = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(error):
            self.assertEqual(main(['check', str(self.root)]), 1)
        self.assertIn('one Unicode Symbol code point', error.getvalue())


if __name__ == '__main__':
    unittest.main()
