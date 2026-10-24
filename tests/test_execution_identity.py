"""Role-aware display from recorded evidence, with no connection or configuration."""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from console_output import execution_identity, execution_identities, execution


class IdentityTests(unittest.TestCase):
    def row(self):
        return {'recipe': {'id': 'mysql-replication'}, 'connected': True,
                'login_identity': {'username': 'operator', 'source': 'ssh_connection'},
                'data': {'instances': [{'instance': 'main', 'server': {'authenticated_user': 'monitor@localhost'}}]}}

    def test_database_and_login_have_explicit_roles_without_os_claim(self):
        row = self.row()
        self.assertEqual(execution_identity(row), 'DB main: monitor@localhost; SSH: operator')
        evidence = execution_identities(row)
        self.assertFalse(any(i['role'] == 'os' for i in evidence))
        self.assertEqual(evidence[0]['source'], 'CURRENT_USER()')

    def test_os_identity_preserves_existing_display_and_overrides_login_fallback(self):
        row = {'access': {'actual_identity': {'username': 'root', 'effective_uid': 0}},
               'connected': True, 'login_identity': {'username': 'operator', 'source': 'ssh_connection'}}
        self.assertEqual(execution_identity(row), 'root (uid=0)')
        row.update(recipe={'id': 'mysql-replication'}, data=self.row()['data'])
        self.assertEqual(execution_identity(row), 'DB main: monitor@localhost; root (uid=0)')

    def test_all_instances_preserve_independent_unknowns_and_same_account_names(self):
        row = self.row()
        row['data']['instances'] += [{'instance': 'other', 'server': None},
                                     {'instance': 'third', 'server': {'authenticated_user': 'monitor@localhost'}}]
        text = execution_identity(row)
        self.assertIn('DB other: unknown', text)
        self.assertIn('DB third: monitor@localhost', text)
        evidence = execution_identities(row)
        self.assertIsNone(evidence[1]['username'])
        self.assertIsNone(evidence[1]['source'])

    def test_configured_accounts_and_unconfirmed_login_never_supply_identity(self):
        row = self.row()
        row['data']['instances'][0] = {'instance': 'main', 'user': 'configured-root', 'server': None}
        self.assertEqual(execution_identity(row), 'SSH: operator')
        row['connected'] = False
        self.assertEqual(execution_identity(row), 'unknown')
        row['connected'] = True
        row['login_identity']['source'] = 'configuration'
        self.assertEqual(execution_identity(row), 'unknown')

    def test_unrelated_recipe_and_control_characters_not_interpreted_as_database_identity(self):
        row = self.row();row['recipe']['id'] = 'other'
        self.assertEqual(execution_identity(row), 'SSH: operator')
        row = self.row();row['data']['instances'][0]['server']['authenticated_user'] = 'bad\x1bname'
        self.assertEqual(execution_identity(row), 'SSH: operator')

    def test_read_only_projection_and_completion_rendering(self):
        row = self.row();row.update(host_id='synthetic', status='success')
        before = copy.deepcopy(row)
        evidence = execution_identities(row)
        self.assertEqual(execution_identity({'identity_evidence': json.loads(json.dumps(evidence))}),
                         execution_identity(row))
        text = execution(row)
        self.assertIn('monitor@localhost', text)
        self.assertIn('SSH: operator', text)
        self.assertEqual(row, before)


if __name__ == '__main__':
    unittest.main()
