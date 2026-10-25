"""Completion labels over synthetic saved findings; no host operations."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from console_output import execution_result, replication_health


class ReplicationCompletionTests(unittest.TestCase):
    def row(self, health='healthy', status='success'):
        return {'recipe': {'id': 'mysql-replication'}, 'status': status,
                'data': {'instances': [{'instance': 'main', 'health': health,
                          'cleanup': 'confirmed', 'reason': 'replica_side_healthy'}]}}

    def test_health_labels_preserve_collection_status_and_raw_data(self):
        for health, state, label in [('healthy', 'success', 'HEALTHY'),
                ('unhealthy', 'partial', 'UNHEALTHY'), ('unknown', 'partial', 'UNKNOWN'),
                ('not_configured', 'partial', 'NOT CONFIGURED')]:
            row = self.row(health, state); before = copy.deepcopy(row)
            self.assertEqual(execution_result(row), {'status': state, 'text': label})
            self.assertEqual(row, before)

    def test_missing_or_uncertain_evidence_never_reports_healthy(self):
        for state in ('partial', 'unknown'):
            self.assertEqual(replication_health(self.row(status=state)), 'UNKNOWN')
        row = self.row(); row['data']['instances'][0]['cleanup'] = 'unknown'
        self.assertEqual(replication_health(row), 'UNKNOWN')
        row['data']['instances'] = []
        self.assertEqual(replication_health(row), 'UNKNOWN')

    def test_query_and_connection_failures_are_errors_not_unhealthy(self):
        for reason in ('query_failed', 'timeout', 'probe_failed', 'client_unavailable',
                       'unsupported_server_version'):
            row = self.row('unknown', 'partial'); row['data']['instances'][0]['reason'] = reason
            self.assertEqual(replication_health(row), 'ERROR')
        self.assertEqual(replication_health(self.row(status='failed')), 'ERROR')

    def test_multiple_instances_do_not_hide_failures_or_mixed_configuration(self):
        row = self.row(); row['data']['instances'].append(self.row('unhealthy')['data']['instances'][0])
        self.assertEqual(replication_health(row), 'UNHEALTHY')
        row['data']['instances'][1]['health'] = 'not_configured'
        self.assertEqual(replication_health(row), 'UNKNOWN')

    def test_compact_projection_matches_full_report_and_other_recipes_keep_pass(self):
        row = self.row()
        projected = {'status': row['status'], 'replication_health': replication_health(row)}
        self.assertEqual(execution_result(projected), execution_result(row))
        for state in ('skipped', 'unsupported'):
            skipped = self.row(status=state)
            self.assertIsNone(replication_health(skipped))
        row['recipe']['id'] = 'other'
        self.assertIsNone(replication_health(row))
        self.assertEqual(execution_result(row)['text'], 'PASS')

    def test_retention_and_publication_failures_remain_visible(self):
        for receipt, reason in [('retention', 'retention_failed'), ('content_update', 'content_update_failed')]:
            row = self.row(); row[receipt] = {'status': 'failed'}
            result = execution_result(row)
            self.assertEqual(result['status'], 'failed')
            self.assertIn(reason, result['text'])
            self.assertIn('HEALTHY', result['text'])


if __name__ == '__main__':
    unittest.main()
