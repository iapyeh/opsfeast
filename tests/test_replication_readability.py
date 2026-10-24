"""Readable status over synthetic retained findings; no database or host execution."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import vault_content as content


class ReplicationReadabilityTests(unittest.TestCase):
    def data(self, health='healthy'):
        return {'status': 'success' if health == 'healthy' else 'partial',
                'policy': {'max_delay_seconds': 60},
                'instances': [{'instance': 'main', 'health': health,
                    'reason': 'replica_side_healthy' if health == 'healthy' else 'channel_unhealthy',
                    'observed_at': '2026-10-24T00:00:00+00:00', 'cleanup': 'confirmed',
                    'server': {'product': 'mysql', 'version': '8.0.46',
                               'hostname': 'synthetic', 'authenticated_user': 'monitor@localhost'},
                    'channels': [{'channel': '', 'source_host': 'source.example',
                        'io_running': 'Yes' if health == 'healthy' else 'No', 'sql_running': 'Yes',
                        'delay_seconds': 0 if health == 'healthy' else None, 'health': health,
                        'reasons': [] if health == 'healthy' else ['thread_not_running', 'incomplete_status']}]}]}

    def record(self, data):
        return {'host_id': 'node', 'record_id': 'synthetic',
                'observed_at': '2026-10-24T00:00:00+00:00',
                'retention_definition': {'contract': 'mysql-replication'}, 'data': data}

    def test_healthy_status_precedes_contents_and_is_not_a_dense_sentence(self):
        rendered = content.render_current(self.record(self.data()))
        self.assertLess(rendered.index('### ✅ HEALTHY'), rendered.index('## Contents'))
        self.assertIn('> [!success] ✅ HEALTHY', rendered)
        self.assertIn('| Observed | 2026-10-24 08:00:00 |', rendered)
        self.assertIn('| Credential cleanup | ✅ Confirmed |', rendered)
        self.assertNotIn('Health: healthy; reason:', rendered)
        self.assertIn('| Reported delay | 0 seconds |', rendered)

    def test_unhealthy_has_red_alert_and_readable_saved_reasons(self):
        rendered = content.render_current(self.record(self.data('unhealthy')))
        self.assertLess(rendered.index('### 🔴 UNHEALTHY'), rendered.index('## Contents'))
        self.assertIn('> [!danger] 🔴 UNHEALTHY', rendered)
        self.assertIn('An I/O or SQL replication thread is not running.', rendered)
        self.assertIn('**Attention required:**', rendered)
        self.assertIn('| I/O thread | No |', rendered)
        self.assertIn('| Reported delay | Not reported |', rendered)
        self.assertNotIn('Some data was not obtained.', rendered)

    def test_unknown_and_cleanup_uncertainty_cannot_have_healthy_overall_banner(self):
        for data in (self.data('unknown'), self.data()):
            data['instances'][0]['cleanup'] = 'unknown'
            self.assertEqual(content.replication_status(data), 'unknown')
            rendered = content.render_current(self.record(data))
            self.assertIn('> [!warning] ⚠️ UNKNOWN', rendered)
            self.assertIn('⚠️ UNKNOWN — not confirmed', rendered)
            self.assertNotIn('> [!success] ✅ HEALTHY', rendered)
        data = self.data(); data['status'] = 'partial'
        self.assertEqual(content.replication_status(data), 'unknown')

    def test_not_configured_and_mixed_states_remain_distinct(self):
        data = self.data('not_configured'); data['instances'][0]['channels'] = []
        data['instances'][0]['reason'] = 'no_replication_channels'
        self.assertEqual(content.replication_status(data), 'not_configured')
        self.assertIn('⚪ NOT CONFIGURED', content.render_current(self.record(data)))
        data['instances'].append(self.data()['instances'][0])
        data['instances'][1]['instance'] = 'secondary'
        self.assertEqual(content.replication_status(data), 'attention')

    def test_all_instances_and_channels_keep_independent_badges(self):
        data = self.data()
        unhealthy = self.data('unhealthy')['instances'][0]; unhealthy['instance'] = 'secondary'
        unhealthy['channels'][0]['channel'] = 'orders'
        data['instances'].append(unhealthy)
        self.assertEqual(content.replication_status(data), 'unhealthy')
        rendered = content.render_current(self.record(data))
        self.assertIn('| main | ✅ HEALTHY |', rendered)
        self.assertIn('| secondary | 🔴 UNHEALTHY |', rendered)
        self.assertIn('#### Channel: orders', rendered)
        self.assertIn('#### Channel: (default)', rendered)

    def test_complete_report_evidence_and_retained_input_are_preserved(self):
        data = self.data('unhealthy'); data['instances'][0]['source_log_file'] = 'binlog.000123'
        before = copy.deepcopy(data)
        report = '\n'.join(content.replication_lines(data, current=False))
        self.assertIn('binlog.000123', report)
        self.assertIn('Full sanitized evidence', report)
        self.assertEqual(data, before)
        current = '\n'.join(content.replication_lines(data, current=True))
        self.assertNotIn('Full sanitized evidence', current)
        self.assertIn('Saved reasons', current)

    def test_tables_use_two_columns_and_preserve_omitted_source_as_unknown(self):
        data = self.data(); data['instances'][0]['channels'][0]['source_host'] = None
        rendered = '\n'.join(content.replication_lines(data, current=True))
        self.assertIn('| Source | Not reported |', rendered)
        for line in rendered.splitlines():
            if line.startswith('|'):
                self.assertEqual(line.count('|'), 3, line)


if __name__ == '__main__':
    unittest.main()
