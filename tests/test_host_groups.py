"""Public synthetic group catalog, expansion and shared-consumer tests; no SSH."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from opsfeast import ConfigError, Instance, Validator, main
from management_view import hosts_snapshot
from recipe_runner import select_hosts


LOCAL = {'connection': {'local': True}}


class HostGroupsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def write(self, data, filename='hosts.yaml'):
        path = self.root / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
        return path

    def config(self):
        return Validator(self.root).check()

    def test_metadata_defaults_explicit_and_implicit_groups(self):
        self.write({'groups': {'backup': {'label': 'BACKUP-SERVERS', 'description': 'Backup files'}, 'empty': {}},
                    'hosts': {'h': dict(LOCAL, group=['backup', 'implicit', 'implicit'])}})
        cfg = self.config()
        self.assertEqual(cfg.groups, {
            'backup': {'label': 'BACKUP-SERVERS', 'description': 'Backup files', 'icon': {}, 'hosts': ['h']},
            'empty': {'label': 'empty', 'description': '', 'icon': {}, 'hosts': []},
            'implicit': {'label': 'implicit', 'description': '', 'icon': {}, 'hosts': ['h']}})
        self.assertEqual(cfg.hosts['h']['group'], ['backup', 'implicit', 'implicit'])

    def test_bulk_memberships_prepend_deduplicate_and_preserve_source(self):
        for membership, expected in ((None, ['backup']), ('linux', ['backup', 'linux']),
                ([], ['backup']), (['production', 'backup', 'linux', 'production'], ['backup', 'production', 'linux'])):
            with self.subTest(membership=membership):
                host = copy.deepcopy(LOCAL)
                if membership is not None:
                    host['group'] = membership
                data = {'groups': {'backup': {'hosts': {'h': host}}}}
                path = self.write(data)
                original = path.read_bytes()
                cfg = self.config()
                self.assertEqual(cfg.hosts['h']['group'], expected)
                self.assertEqual(cfg.groups['backup']['hosts'], ['h'])
                self.assertEqual(cfg.documents[path], data)
                self.assertEqual(path.read_bytes(), original)
                self.assertEqual(cfg.sources['h'], path)

    def test_icons_resolve_after_all_includes_per_field_with_named_user_override(self):
        self.write({'default': {'icon': {'host': '☀', 'user': '★'}, 'users': {'alice': {'icon': '👩'}}},
                    'include': ['hosts/first.yaml', 'groups/last.yaml']})
        self.write({'hosts': {'early': dict(LOCAL, group=['backup', 'linux'], users={'alice': {}, 'bob': {}})}}, 'hosts/first.yaml')
        self.write({'groups': {'backup': {'icon': {'host': '🗂'}, 'hosts': {
            'bulk': dict(LOCAL, group=['linux', 'backup'], users={'alice': {'icon': '♠'}, 'bob': {}})}},
            'linux': {'icon': {'host': '🐧', 'user': '👨'}}}}, 'groups/last.yaml')
        cfg = self.config()
        for name in ('early', 'bulk'):
            self.assertEqual(cfg.hosts[name]['icon'], '🗂')
            self.assertEqual(cfg.hosts[name]['users']['bob']['icon'], '👨')
        self.assertEqual(cfg.hosts['early']['users']['alice']['icon'], '👩')
        self.assertEqual(cfg.hosts['bulk']['users']['alice']['icon'], '♠')
        self.assertEqual(cfg.groups['backup']['hosts'], ['early', 'bulk'])
        self.assertEqual(cfg.sources['bulk'], self.root / 'groups/last.yaml')
        self.assertEqual(cfg.groups['linux']['hosts'], ['early', 'bulk'])

    def test_duplicate_hosts_rejected_across_all_containers(self):
        for data in (
            {'hosts': {'h': LOCAL}, 'groups': {'a': {'hosts': {'h': LOCAL}}}},
            {'groups': {'a': {'hosts': {'h': LOCAL}}, 'b': {'hosts': {'h': LOCAL}}}},
            {'include': ['extra.yaml'], 'groups': {'a': {'hosts': {'h': LOCAL}}}},
        ):
            self.write({'hosts': {'h': LOCAL}}, 'extra.yaml')
            self.write(data)
            with self.subTest(data=data), self.assertRaisesRegex(ConfigError, 'duplicate host h'):
                self.config()

    def test_duplicate_group_definitions_rejected_but_shared_membership_allowed(self):
        self.write({'groups': {'a': {}}}, 'extra.yaml')
        self.write({'include': ['extra.yaml'], 'groups': {'a': {}}})
        with self.assertRaisesRegex(ConfigError, 'duplicate group a'):
            self.config()
        self.write({'hosts': {'h': dict(LOCAL, group='a')}}, 'extra.yaml')
        cfg = self.config()
        self.assertEqual(cfg.groups['a']['hosts'], ['h'])

    def test_invalid_group_shapes_and_values(self):
        invalid = (None, [], {'': {}}, {1: {}}, {'a': None}, {'a': []}, {'a': {'label': ''}},
                   {'a': {'label': None}}, {'a': {'label': 1}}, {'a': {'label': 'x\x00y'}},
                   {'a': {'description': None}}, {'a': {'description': 1}}, {'a': {'description': 'x\x00y'}},
                   {'a': {'icon': None}}, {'a': {'icon': {'other': '★'}}}, {'a': {'icon': {'host': '☀️'}}},
                   {'a': {'hosts': None}}, {'a': {'hosts': []}}, {'a': {'hosts': {'h': None}}},
                   {'a': {'hosts': {'h': dict(LOCAL, group=None)}}}, {'a': {'unknown': {}}})
        for groups in invalid:
            self.write({'groups': groups})
            with self.subTest(groups=groups), self.assertRaises(ConfigError):
                self.config()
        self.write({'host-groups': {}})
        with self.assertRaises(ConfigError):
            self.config()
        self.write({'groups': {'a': {'hosts': {'h': dict(LOCAL, users={'operator': {'sudo': 'false'}})}}}})
        with self.assertRaises(ConfigError):
            self.config()

    def test_legacy_group_defaults_rejected_with_migration_hint(self):
        for data in ({'default': {'groups': {}}},
                     {'default': {'groups': {'a': {'icon': {'host': '★'}}}}, 'groups': {'a': {}}}):
            self.write(data)
            with self.subTest(data=data), self.assertRaisesRegex(ConfigError, 'default.groups has moved to top-level groups'):
                self.config()

    def test_selection_uses_ids_unifies_memberships_and_recognizes_empty_groups(self):
        self.write({'groups': {'backup': {'label': 'BACKUP-SERVERS', 'hosts': {
            'first': dict(LOCAL, group='linux'), 'disabled': dict(LOCAL, enabled=False)}}, 'empty': {}},
            'hosts': {'top': dict(LOCAL, group='backup')}})
        excluded = []
        self.assertEqual(select_hosts(self.root, [('group', 'backup'), ('group', 'linux')], excluded=excluded), ['top', 'first'])
        self.assertEqual(excluded, [{'host': 'disabled', 'reason_code': 'host_disabled'}])
        with self.assertRaisesRegex(ConfigError, 'unknown group'):
            select_hosts(self.root, [('group', 'BACKUP-SERVERS')])
        with self.assertRaisesRegex(ConfigError, 'no hosts selected'):
            select_hosts(self.root, [('group', 'empty')])
        self.assertEqual(select_hosts(self.root, [('host', 'first')]), ['first'])

    def test_bulk_hosts_keep_relative_recipe_paths_and_jump_references(self):
        from attribution_fixture import copy_recipe
        from opsfeast import REPOSITORY_RECIPES
        directory = self.root / 'parts/recipes/identity'
        copy_recipe(REPOSITORY_RECIPES / 'system/account/check/identity', directory)
        self.write({'include': ['parts/hosts.yaml'], 'hosts': {'jump': {
            'connection': {'hostname': 'jump.invalid', 'allow_agent': True}}}})
        path = self.write({'groups': {'backup': {'hosts': {'target': {
            'connection': {'hostname': 'target.invalid', 'allow_agent': True, 'via': {'host': 'jump'}},
            'recipes': [{'recipe': './recipes/identity'}]}}}}}, 'parts/hosts.yaml')
        cfg = self.config()
        self.assertEqual(cfg.selected['target'], [directory])
        self.assertEqual(cfg.sources['target'], path)
        self.assertEqual(cfg.edges['target'], ['jump'])
        from opsfeast import connection_plan
        from unittest.mock import Mock
        resolver = Mock()
        resolver.resolve_connection.side_effect = lambda host, **kw: dict(hostname=host, **{k: v for k, v in kw.items() if k != 'ssh_config'})
        self.assertEqual(len(connection_plan(cfg, 'target', resolver)), 2)

    def test_cli_core_snapshot_and_ui_share_catalog_without_host_credentials(self):
        self.write({'groups': {'backup': {'label': 'BACKUP-SERVERS', 'description': 'Backup files',
            'hosts': {'h': dict(LOCAL, users={'operator': {'password': 'SYNTHETIC-SECRET'}})}}}})
        profile = Instance.open(self.root).profile(root=self.root)
        catalog = profile.hosts.groups()
        self.assertEqual(catalog['backup']['hosts'], ['h'])
        self.assertNotIn('SYNTHETIC-SECRET', json.dumps(catalog))
        catalog['backup']['hosts'].clear()
        self.assertEqual(profile.hosts.groups()['backup']['hosts'], ['h'])
        self.assertEqual(profile.inspect()['groups'], profile.hosts.groups())
        with patch('opsfeast.resolve_root', return_value=self.root), \
                patch('opsfeast.load_profiles', return_value={'default_profile': 'main'}):
            snapshot = hosts_snapshot()
        self.assertEqual(snapshot['groups'], profile.hosts.groups())
        self.assertNotIn('SYNTHETIC-SECRET', json.dumps(snapshot))
        for key, expected in (('groups', profile.hosts.groups()), ('groups.backup.hosts', ['h']), ('hosts.h.group', ['backup'])):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(['dump', key, str(self.root)]), 0)
            self.assertEqual(json.loads(output.getvalue()), expected)
        self.write({'groups': {'backup': {'label': 'UPDATED'}}})
        self.assertEqual(profile.hosts.groups()['backup']['label'], 'BACKUP-SERVERS')
        self.assertEqual(profile.inspect()['groups']['backup']['label'], 'UPDATED')
        profile.reload()
        self.assertEqual(profile.hosts.groups()['backup']['label'], 'UPDATED')
        self.write({'groups': {'backup': {'description': None}}})
        with self.assertRaises(ConfigError):
            profile.reload()
        self.assertEqual(profile.hosts.groups()['backup']['label'], 'UPDATED')


if __name__ == '__main__':
    unittest.main()
