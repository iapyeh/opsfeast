"""Explicit agent launch guidance; no browser, network, host or invoice execution."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
from opsfeast import ConfigError
from opsfeast.recipe_launch import describe
from opsfeast.recipe_runs import prepare_pair, RecipeRunError


class RecipeLaunchTests(unittest.TestCase):
    def test_direct_default_and_agent_prompt_validation(self):
        self.assertEqual(describe({}), {'mode':'direct','prompt':'','river':False})
        self.assertEqual(describe({'launch':{'mode':'agent','prompt':'Read this recipe.'}})['mode'],'agent')
        for value in [None,{}, {'mode':'other'}, {'mode':'agent'}, {'mode':'agent','prompt':' '},
                      {'mode':'agent','prompt':'x'*8001}, {'mode':'agent','prompt':'\x00'},
                      {'mode':'agent','prompt':'ok','execute':True}, {'mode':'agent','prompt':'ok','river':'yes'}, {'mode':'agent','prompt':'ok','river':1}]:
            with self.subTest(value=str(value)[:100]),self.assertRaises(ConfigError):describe({'launch':value})

    def test_river_requires_workflow_contract_and_boolean_opt_in(self):
        launch={'mode':'agent','prompt':'Synthetic task.','river':True}
        self.assertTrue(describe({'runner':{'contract':'python-workflow'},'launch':launch})['river'])
        for runner in ('invalid',{'contract':'python-session'},{'contract':'python-report'}):
            with self.subTest(runner=runner),self.assertRaises(ConfigError):describe({'runner':runner,'launch':launch})

    def test_web_preflight_rejects_agent_before_host_connection_or_process(self):
        item={'reference':':synthetic/browser','runnable':True,'kind':'operation',
              'descriptor':{'launch':{'mode':'agent','prompt':'Arrange browser first.'}}}
        with patch('recipe_catalog.choose',return_value=item),patch('recipe_runner.preflight') as preflight,patch('subprocess.Popen') as process:
            with self.assertRaisesRegex(RecipeRunError,'agent_launch_required'):
                prepare_pair(Path('/synthetic'),item['reference'],'synthetic-host',{},[])
            preflight.assert_not_called();process.assert_not_called()

    def test_catalog_and_content_keep_static_readiness_separate_from_web_launch(self):
        from test_general_recipes import GeneralRecipeTests
        from opsfeast.recipe_authoring import inspect
        from types import SimpleNamespace
        from recipe_catalog import choose
        fixture=GeneralRecipeTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.metadata['launch']={'mode':'agent','prompt':'Synthetic browser task.'};fixture.write()
        item=choose(fixture.root,':system/network/check/port')
        self.assertTrue(item['runnable']);self.assertFalse(item['web_runnable'])
        content=inspect(SimpleNamespace(root=fixture.root,name='synthetic'),item['reference'])
        self.assertEqual(content['launch'],dict(fixture.metadata['launch'],river=False));self.assertFalse(content['web_runnable'])
        # Agent-started CLI/runner remains available; Web launch restriction is not a runner ban.
        report,_=fixture.execute(assignments=['port=8888'])
        self.assertEqual(report['status'],'success')

    def test_nested_user_meal_cannot_bypass_agent_launch_boundary(self):
        from test_recipe_library import RecipeLibraryTests
        from opsfeast.recipe_runs import RecipeRuns
        fixture=RecipeLibraryTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        descriptor=fixture.root/'recipes/system/network/check/local-port/recipe.yaml'
        from opsfeast import read_yaml
        metadata=read_yaml(descriptor);metadata['launch']={'mode':'agent','prompt':'Synthetic agent task.'};metadata['execution']['stages'][0]['executor']='agent'
        descriptor.write_text(json.dumps(metadata))
        child=fixture.change('set.create',fixture.meal([fixture.reference]))['sets'][-1]
        parent=fixture.change('set.create',fixture.meal(meals=[child['id']]))['sets'][-1]
        service=RecipeRuns(fixture.product,fixture.product);self.addCleanup(service.close)
        body={'profile':'main','hosts':['node'],'recipes':[],'meals':[parent['id']],'timeout':30}
        with patch('subprocess.Popen') as process,patch('recipe_runner.preflight') as preflight:
            with self.assertRaisesRegex(RecipeRunError,'agent_launch_required'):service.preview(body)
            process.assert_not_called();preflight.assert_not_called()
