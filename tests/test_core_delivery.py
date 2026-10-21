"""Public Core recipe runner, static discovery and package installation regressions."""
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_backend
from opsfeast import Instance
import recipe_runner as run_recipe
from recipe_inspection import inspect_one
from recipe_catalog import catalog
from test_core_api import Actor

ROOT = Path(__file__).resolve().parents[1]
CODE = '''VERSION = '0.1.0'
SAVED = None
def execute(recipe):
    global SAVED
    SAVED = recipe
    with recipe.sudo() as privileged:
        result = privileged.session.exec_command(['whoami'])
    return {'status': 'success', 'reason_code': 'observed', 'message': 'Synthetic observation.',
            'data': {'account': result.stdout.strip(), 'input': recipe.vars['value']}}
'''


class CoreDeliveryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.instance = Instance.open(self.root)
        with redirect_stdout(io.StringIO()):
            self.profile = self.instance.init_profile()
        (self.profile.root / 'hosts.yaml').write_text(json.dumps({'hosts': {'h': {'connection': {'local': True},
            'users': {'operator': {'password': 'private-value'}}}}}))
        self.directory = self.profile.root / 'recipes/example'
        self.directory.mkdir(parents=True)
        self.meta = {'descriptor_version': '0.3.0', 'id': 'core-example', 'version': '0.1.0',
                     'author': {'name': 'Synthetic', 'contacts': ['synthetic@example.invalid']}, 'license': 'MIT',
                     'runner': {'contract': 'python-recipe', 'version': '0.1.0', 'entrypoint': 'main.py'},
                     'inputs': {'variables': {'value': {'type': 'integer', 'default': 7}}},
                     'output': {'schema_version': '0.1.0'}}
        self.write()

    def write(self, code=CODE):
        (self.directory / 'recipe.yaml').write_text(json.dumps(self.meta))
        (self.directory / 'main.py').write_text(code)

    def run_recipe(self, actor=None):
        actor = actor or Actor()
        with patch.object(run_recipe, 'REPOSITORY_ROOT', self.root):
            return run_recipe.run(self.profile.root, 'h', recipe=':example', session_class=lambda: actor)

    def test_runner_core_context_results_and_unchanged_raw_contract(self):
        report, path = self.run_recipe()
        self.assertEqual(report['status'], 'success', report)
        self.assertEqual(report['data'], {'account': 'root', 'input': 7})
        self.assertEqual(report['instance']['id'], self.instance.identity['id'])
        self.assertEqual(report['profile'], 'main')
        self.assertTrue(report['privileges'][0]['restoration_verified'])
        self.assertEqual(report['recipe']['runner_contract'], 'python-recipe')
        self.assertEqual(report['retention']['reason_code'], 'no_retention_adapter')
        self.assertNotIn('private-value', path.read_text())

    def test_static_catalog_and_signature_never_import_recipe(self):
        self.write("raise RuntimeError('must not execute')\n" + CODE)
        inspected = inspect_one(self.directory, [])
        self.assertEqual(inspected['runner_contract'], 'valid-python-recipe')
        item = next(item for item in catalog(self.profile.root)['recipes'] if item['id'] == 'core-example')
        self.assertTrue(item['runnable'])
        self.write(CODE.replace('def execute(recipe):', 'def execute(recipe, required):'))
        self.assertEqual(inspect_one(self.directory, [])['status'], 'failed')

    def test_runner_cleanup_failure_overrides_success_and_redacts_error_text(self):
        actor = Actor()
        actor.close_failure = True
        report, path = self.run_recipe(actor)
        self.assertEqual(report['reason_code'], 'cleanup_failed')
        self.assertNotIn('synthetic-private-password', path.read_text())

    def test_runner_does_not_allow_swallowed_restoration_failure_success(self):
        self.write('''VERSION = '0.1.0'
def execute(recipe):
    try:
        with recipe.sudo():
            pass
    except RuntimeError:
        pass
    return {'status': 'success', 'reason_code': 'claimed', 'message': 'Claim.', 'data': {}}
''')
        actor = Actor()
        actor.restore_failure = True
        report, _ = self.run_recipe(actor)
        self.assertEqual(report['reason_code'], 'cleanup_failed')

    def test_concurrent_identity_initialization_produces_one_identity(self):
        from concurrent.futures import ThreadPoolExecutor
        other = self.root / 'other'
        other.mkdir()
        instance = Instance.open(other)
        with ThreadPoolExecutor(max_workers=4) as pool:
            ids = list(pool.map(lambda _: instance.initialize()['id'], range(8)))
        self.assertEqual(len(set(ids)), 1)

    def test_bundled_identity_recipe_success_truncation_and_invalid_output(self):
        import runpy
        execute = runpy.run_path(str(ROOT / 'recipes/system/account/check/identity/main.py'))['execute']
        from types import SimpleNamespace
        for text, truncated, status in [('operator\n', False, 'success'), ('operator', True, 'failed'), ('one\ntwo', False, 'failed')]:
            result = SimpleNamespace(stdout=text, stdout_truncated=truncated, stderr_truncated=False)
            session = SimpleNamespace(exec_command=lambda *args, **kwargs: result)
            observed = execute(SimpleNamespace(session=session))
            self.assertEqual(observed['status'], status)

    def test_wheel_and_sdist_public_allowlist_and_isolated_import(self):
        wheel = self.root / build_backend.build_wheel(str(self.root))
        first = hashlib.sha256(wheel.read_bytes()).hexdigest()
        build_backend.build_wheel(str(self.root))
        self.assertEqual(hashlib.sha256(wheel.read_bytes()).hexdigest(), first)
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
            metadata = archive.read(next(name for name in names if name.endswith('.dist-info/METADATA'))).decode()
            self.assertIn('Requires-Dist: tabulate[widechars]==0.10.0\n', metadata)
            self.assertIn('tabulate[widechars]==0.10.0', archive.read('_opsfeast_data/requirements-init.txt').decode())
            self.assertIn('opsfeast/core.py', names)
            self.assertIn('_opsfeast_data/tools/console_output.py', names)
            self.assertIn('_opsfeast_data/tools/observation_results.py', names)
            self.assertIn('_opsfeast_data/tools/cli_help.py', names)
            self.assertIn('_opsfeast_data/tools/collection_evidence.py', names)
            self.assertIn('_opsfeast_data/schemas/collection-evidence.schema.json', names)
            self.assertIn('_opsfeast_data/tools/root_access.py', names)
            self.assertIn('_opsfeast_data/tools/retention_store.py', names)
            self.assertIn('_opsfeast_data/tools/retention_contracts.py', names)
            self.assertIn('_opsfeast_data/recipes/system/inventory/overview/retention.py', names)
            self.assertIn('_opsfeast_data/recipes/system/inventory/overview/retention.schema.json', names)
            self.assertIn('_opsfeast_data/tools/vault_content.py', names)
            self.assertIn('_opsfeast_data/tools/retention_consumers.py', names)
            self.assertIn('_opsfeast_data/consumers/vault/consumer.yaml', names)
            self.assertIn('_opsfeast_data/consumers/vault/main.py', names)
            self.assertIn('_opsfeast_data/schemas/retention-consumer.schema.json', names)
            self.assertIn('_opsfeast_data/schemas/retention-event.schema.json', names)
            self.assertIn('_opsfeast_data/schemas/retention-selection.schema.json', names)
            self.assertIn('_opsfeast_data/recipes/feast/report/retention-summary/main.py', names)
            self.assertIn('_opsfeast_data/tests/test_core_delivery.py', names)
            self.assertIn('_opsfeast_data/recipes/system/network/check/port/LICENSE', names)
            for reference in ('system/network/check/port', 'system/account/check/identity', 'system/inventory/overview',
                              'feast/report/execution-summary', 'feast/report/retention-summary'):
                self.assertIn('_opsfeast_data/recipes/' + reference + '/recipe.yaml', names)
            self.assertFalse(any(name.startswith(('_opsfeast_data/recipes/check/', '_opsfeast_data/recipes/inventory/',
                                                  '_opsfeast_data/recipes/report/')) for name in names))
            self.assertFalse(any('AGENTS.local' in name or '__pycache__' in name or '.opsfeast-instance' in name for name in names))
            target = self.root / 'wheel-install'
            archive.extractall(target)
        code = '''import sys
sys.path.insert(0, sys.argv[1])
sys.path.append(sys.argv[3])  # Selected environment's dependency directory, not checkout source.
from pathlib import Path
from opsfeast import Instance, Recipe, RootUnavailableError, CoreError
assert callable(Recipe.root)
assert issubclass(RootUnavailableError, CoreError)
from root_access import candidates
from recipe_inspection import inspect_one
root = Path(sys.argv[2])
instance = Instance.open(root)
assert instance.inspect()['identity']['identity_status'] == 'placeholder'
from opsfeast import REPOSITORY_RECIPES
assert inspect_one(REPOSITORY_RECIPES / 'system/network/check/port', [])['status'] == 'success'
from retention_store import retain_general
from recipe_catalog import choose
from recipe_reports import run_report
from uuid import uuid4
profile = instance.init_profile('smoke')
metadata = {'id':'synthetic-check','version':'1','access_mode':'read','retention':{
    'contract':'host-values','version':'0.2.0','description':'Synthetic count only.',
    'fields':{'count':{'type':'integer','unit':'items','description':'Observed count'}}}}
raw = {'host_id':'node','status':'partial','evidence_kind':'local','completed_at':'2026-10-19T00:00:00Z',
       'recipe':{'id':'synthetic-check','version':'1','reference':'alpha:check/count'},
       'data':{'count':0},'execution_access_mode':'read','source_observation_id':str(uuid4())}
receipt = retain_general(profile.root, raw, metadata, profile.root)
assert receipt['status'] == 'stored' and receipt['content_update']['status'] == 'success'
assert profile.retention.query()['records'][0]['data']['observations']['count']['value'] == 0
from contextlib import redirect_stdout
from io import StringIO
from opsfeast import main
import json
raw_path = profile.root/'observations/synthetic.json'
raw_path.write_text(json.dumps(raw))
with redirect_stdout(StringIO()) as captured:
    assert main(['observation','result','observations/synthetic.json','--raw','--root',str(profile.root)]) == 0
assert json.loads(captured.getvalue()) == raw
with redirect_stdout(StringIO()) as captured:
    assert main(['recipes','results','list','--json','--root',str(profile.root)]) == 0
assert json.loads(captured.getvalue())['results'] == []
assert not list((profile.root/'vault').rglob('*.sqlite3'))
report, path = run_report(profile.root, choose(profile.root, 'feast/report/retention-summary'), [])
assert report['status'] == 'success' and len(report['artifacts']) == 2
assert report['retention_sources'][0]['records']
import json
from retention_store import retain
inventory_raw = json.loads((REPOSITORY_RECIPES/'system/inventory/overview/examples/result.partitioned.synthetic.json').read_text())
receipt = retain(profile.root, inventory_raw)
assert receipt['status'] == 'stored', receipt
record = profile.retention.show(receipt['record_id'])
assert record['retention_definition']['contract'] == 'inventory-observations'
assert record['data']['inventory']['hardware']['memory_total_bytes'] is not None
assert inspect_one(REPOSITORY_RECIPES/'system/inventory/overview', [])['retention']['schema_path'].endswith('retention.schema.json')
from retention_consumers import catalog, dispatch, inspect_deliveries
assert catalog(profile.root)['consumers'][0]['source'] == 'builtin:vault'
assert choose(profile.root, 'system/inventory/overview')['consumers'][0]['id'] == 'vault'
assert len(inspect_deliveries(profile.root)['events']) == 2
local = profile.root/'consumers/counter'
local.mkdir(parents=True)
(local/'consumer.yaml').write_text(json.dumps({'schema_version':'0.1.0','id':'counter',
    'description':'Synthetic installed consumer','entrypoint':'main.py',
    'subscriptions':[{'event':'retention.observation.created','selector':{}}]}))
(local/'main.py').write_text("def execute(context):\\n    (context.root/'counter.txt').write_text(str(len(context.retention.query()['records'])))\\n    return {'status':'success'}\\n")
with (profile.root/'feast.yaml').open('a') as stream:
    stream.write('consumers: {counter: {source: \"local:consumers/counter\", enabled: true}}\\n')
assert dispatch(profile.root, 'counter')['status'] == 'success'
assert (profile.root/'counter.txt').read_text() == '2'
assert len(inspect_deliveries(profile.root, 'counter')['events'][0]['deliveries']) == 1
assert dispatch(profile.root, 'counter')['consumers'] == []
'''
        environment = dict(os.environ)
        environment.pop('PYTHONPATH', None)
        clean = self.root / 'clean'
        clean.mkdir()
        result = subprocess.run([sys.executable, '-B', '-c', code, str(target), str(clean), str(Path(__import__('yaml').__file__).parent.parent)], cwd='/',
                                env=environment, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        sdist = self.root / build_backend.build_sdist(str(self.root))
        import tarfile
        with tarfile.open(sdist) as archive:
            self.assertTrue(any(name.endswith('/tests/test_core_api.py') for name in archive.getnames()))


if __name__ == '__main__':
    unittest.main()
