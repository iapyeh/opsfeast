"""Deep classified recipe paths, unchanged identity and historical retention evidence."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from opsfeast import ConfigError, REPOSITORY_RECIPES, Validator, main, read_yaml
from attribution_fixture import copy_recipe
import recipe_catalog as catalog
import recipe_inspection as inspection
import retention_contracts as contracts
import retention_consumers as consumers
import retention_replay as replay
import retention_store as store
import test_host_vault as vault_fixtures

BUNDLED = {
    'system/network/check/port': ('check-port', '0.1.0'),
    'system/account/check/identity': ('check-identity', '0.1.0'),
    'system/inventory/overview': ('inventory-system', '0.3.1'),
    'feast/report/execution-summary': ('report-summary', '0.1.2'),
    'feast/report/retention-summary': ('report-retention', '0.1.0'),
}


class RecipeTaxonomyTests(unittest.TestCase):
    setUp = vault_fixtures.VaultTests.setUp
    enable = vault_fixtures.VaultTests.enable

    def test_bundle_catalog_keeps_ids_versions_and_has_five_classified_leaves(self):
        result = catalog.catalog()
        self.assertEqual(result['status'], 'success', result)
        self.assertEqual({r['reference']: (r['id'], r['version']) for r in result['recipes']}, BUNDLED)
        self.assertTrue(all(r['runnable'] for r in result['recipes']))
        leaves = {p.parent for p in REPOSITORY_RECIPES.rglob('recipe.yaml')}
        for leaf in leaves:
            self.assertFalse(any(parent in leaves for parent in leaf.parents))
            self.assertTrue((leaf / 'README.md').is_file())
            self.assertTrue((leaf / 'LICENSE').is_file())
        self.assertEqual(len(leaves), 5)

    def test_old_bundle_paths_are_not_aliases_but_ids_remain_selectable(self):
        for old in ('check/port', 'check/identity', 'inventory/system', 'report/summary', 'report/retention'):
            with self.subTest(old=old), self.assertRaises(ConfigError):
                catalog.choose(None, old)
        for reference, (identifier, _) in BUNDLED.items():
            self.assertEqual(catalog.choose(None, identifier)['reference'], reference)

    def test_deep_bundle_inspection_and_cli_do_not_import_execution_code(self):
        with patch('runpy.run_path', side_effect=AssertionError('no execution')):
            result = inspection.inspect_recipes()
            self.assertEqual(result['status'], 'success', result)
            self.assertEqual(len(result['recipes']), 5)
            for reference in BUNDLED:
                self.assertEqual(inspection.inspect_recipes(reference)['status'], 'success')
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = main(['inspect-recipe', reference, '--json'])
                self.assertEqual(code, 0, output.getvalue())

    def test_profile_and_external_sources_accept_more_than_four_levels(self):
        profile_path = 'business/production/system/network/check/port'
        external_path = 'database/mysql/cluster/replication/check/status'
        copy_recipe(REPOSITORY_RECIPES / 'system/network/check/port', self.root / 'recipes' / profile_path)
        external = self.root / 'shared'
        copy_recipe(REPOSITORY_RECIPES / 'system/account/check/identity', external / external_path)
        data = {'recipe_sources': {'company': {'path': str(external)}}, 'hosts': {
            'node': {'connection': {'local': True}, 'recipes': [':' + profile_path, 'company:' + external_path]}}}
        (self.root / 'hosts.yaml').write_text(json.dumps(data))
        selected = Validator(self.root).check()
        self.assertEqual(selected.selected['node'], [self.root / 'recipes' / profile_path, external / external_path])
        found = catalog.catalog(self.root)
        self.assertEqual(found['status'], 'success', found)
        self.assertIn(':' + profile_path, {r['reference'] for r in found['recipes']})
        self.assertEqual(catalog.choose(self.root, 'company:' + external_path)['source'], 'company')

    def test_domain_directory_requires_recursive_selection_and_deep_globs_work(self):
        data = {'hosts': {'node': {'connection': {'local': True}, 'recipes': [
            {'directory': 'system', 'recursive': True}, {'glob': 'system/**/port'}]}}}
        path = self.root / 'hosts.yaml'
        path.write_text(json.dumps(data))
        selected = Validator(self.root).check()
        self.assertEqual([p.relative_to(REPOSITORY_RECIPES).as_posix() for p in selected.selected['node']],
                         ['system/account/check/identity', 'system/inventory/overview', 'system/network/check/port'])
        data['hosts']['node']['recipes'] = [{'directory': 'system', 'recursive': False}]
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ConfigError, 'matched no recipes'):
            Validator(self.root).check()

    def raw(self):
        directory = REPOSITORY_RECIPES / 'system/inventory/overview'
        return json.loads((directory / 'examples/result.partitioned.synthetic.json').read_text())

    def test_saved_snapshot_still_matches_relocated_normalizer_and_schema(self):
        raw = self.raw()
        saved = raw['retention_snapshot']
        selected = replay.select_snapshot(raw)
        self.assertEqual(selected, saved)
        self.assertEqual(saved['normalizer_sha256'], contracts.normalizer_digest(saved['retention']))
        self.assertEqual(saved['schema_sha256'], contracts.schema_digest(saved['retention']))
        module, schema = contracts.location(('inventory-observations', '0.1.0'))
        self.assertEqual(module.parent, REPOSITORY_RECIPES / 'system/inventory/overview')
        self.assertEqual(schema.parent, module.parent)

    def test_historical_reference_and_current_collection_remain_separate(self):
        self.enable()
        historical = self.raw()
        historical['recipe']['reference'] = 'inventory/system'
        historical['source_observation_id'] = str(uuid4())
        before = copy.deepcopy(historical)
        saved = store.retain(self.root, historical)
        self.assertEqual(saved['status'], 'stored')
        self.assertEqual(historical, before)
        record = store.show(self.root, saved['record_id'])
        self.assertEqual(record['recipe_reference'], 'inventory/system')
        self.assertEqual(consumers.events(self.root)[0][1]['recipe_reference'], 'inventory/system')
        current = copy.deepcopy(historical)
        current['source_observation_id'] = str(uuid4())
        current['recipe']['reference'] = 'system/inventory/overview'
        store.retain(self.root, current)
        self.assertEqual(len(store.query(self.root, recipe='inventory/system')['records']), 1)
        self.assertEqual(len(store.query(self.root, recipe='system/inventory/overview')['records']), 1)
        self.assertEqual(store.show(self.root, saved['record_id']), record)
        self.assertEqual(len(store.records(self.root)), 2)

    def test_consumer_exact_new_reference_matches_only_current_events(self):
        self.enable()
        directory = self.root / 'consumers/inventory-index'
        directory.mkdir(parents=True)
        descriptor = {'schema_version': '0.1.0', 'id': 'inventory-index', 'description': 'Synthetic classified inventory consumer.',
                      'entrypoint': 'main.py', 'subscriptions': [{'event': 'retention.observation.created', 'selector': {
                          'recipe_reference': 'system/inventory/overview', 'contract': 'inventory-observations', 'version': '0.1.0'}}]}
        (directory / 'consumer.yaml').write_text(json.dumps(descriptor))
        (directory / 'main.py').write_text("def execute(context):\n    (context.root/'indexed-reference.txt').write_text(context.event['recipe_reference'])\n    return {'status':'success'}\n")
        definition = self.root / 'feast.yaml'
        data = read_yaml(definition)
        data['consumers'] = {'inventory-index': {'source': 'local:consumers/inventory-index', 'enabled': True}}
        definition.write_text(json.dumps(data))
        old = self.raw()
        old['recipe']['reference'] = 'inventory/system'
        old['source_observation_id'] = str(uuid4())
        store.retain(self.root, old)
        self.assertFalse((self.root / 'indexed-reference.txt').exists())
        new = copy.deepcopy(old)
        new['source_observation_id'] = str(uuid4())
        new['recipe']['reference'] = 'system/inventory/overview'
        store.retain(self.root, new)
        self.assertEqual((self.root / 'indexed-reference.txt').read_text(), 'system/inventory/overview')
        relations = catalog.choose(self.root, 'system/inventory/overview')['consumers']
        self.assertEqual({i['id'] for i in relations}, {'vault', 'inventory-index'})


if __name__ == '__main__':
    unittest.main()
