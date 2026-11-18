"""Bounded read-only activity projections; synthetic saved evidence only."""
import unittest
from opsfeast.recipe_activity import activity_summary


class ActivitySummaryTests(unittest.TestCase):
    def test_staged_parent_and_worker_observations_form_one_activity_row(self):
        from opsfeast.recipe_activity import group_web_activity
        parent = {'id': 'plate', 'river_url': '/console/plate/history', 'stage': None}
        workers = [{'id': 'batch-' + host, 'web_run_id': 'plate', 'time': '2026-11-18T01:00:00Z',
                    'title': 'Recipe', 'recipe_reference': 'system/inventory/hardware',
                    'recipe_titles': ['Recipe'], 'meal_titles': [], 'status': 'success',
                    'details': {'targets': [{'host_id': host, 'status': 'success', 'retention_status': 'stored'}]},
                    'result_links': [{'result_id': host + '.json', 'host_id': host}]} for host in ('a', 'b')]
        for items in ([parent, *workers], [*workers, parent]):
            (row,) = group_web_activity(items)
            self.assertEqual(row['id'], 'plate')
            self.assertEqual(row['river_url'], parent['river_url'])
            self.assertEqual(len(row['result_links']), 2)
            self.assertEqual({target['host_id'] for target in row['details']['targets']}, {'a', 'b'})

    def test_pipeline_stages_missing_data_and_successful_receipts_are_independent(self):
        run={'targets':[{'host_id':'node','status':'partial','reason_code':'package_security_pipeline_incomplete','retention_status':'stored'}]}
        raw={'data':{'stages':[{'stage':'collection','status':'partial','reason_code':'os_package_inventory_incomplete','private_vars':'omit'},{'stage':'advisories','status':'failed','reason_code':'vendor_distribution_unsupported_or_unidentified'},{'stage':'report','status':'partial','reason_code':'package_security_report_incomplete'}],'gaps':['vendor_distribution_unsupported_or_unidentified'],'package_snapshot':{'complete':False,'collected_count':0,'packages':[{'private':'omit'}],'gaps':['package_database_changed_during_collection'],'platform_details':{'gaps':['esxi_xml_unparseable:system version get']}}},'retention':{'status':'stored'},'content_update':{'status':'success'}}
        result=activity_summary(run,[{'host_id':'node','result_id':'observations/synthetic.json','raw':raw}])
        self.assertEqual(result['incomplete_hosts'],1);issue=result['issues'][0]
        self.assertEqual(len(issue['stages']),3);self.assertEqual(issue['packages']['collected_count'],0)
        self.assertEqual(issue['receipts'],{'retention':'stored','content_update':'success'})
        self.assertIn('esxi_xml_unparseable:system version get',issue['gaps'])
        self.assertNotIn('private',str(result))

    def test_missing_raw_does_not_invent_success_and_rows_are_bounded(self):
        run={'targets':[{'host_id':'ok','status':'success','retention_status':'stored'},*[{'host_id':str(i),'status':'unsupported'} for i in range(25)]]}
        result=activity_summary(run)
        self.assertEqual(result['completed_hosts'],1);self.assertEqual(result['incomplete_hosts'],25)
        self.assertEqual(len(result['issues']),20);self.assertEqual(result['omitted_hosts'],5)
        self.assertNotIn('stages',result['issues'][0])

    def test_failed_retention_is_not_completed_collection(self):
        result=activity_summary({'targets':[{'host_id':'node','status':'success','retention_status':'failed'}]})
        self.assertEqual(result['incomplete_hosts'],1);self.assertEqual(result['issues'][0]['status'],'success')
