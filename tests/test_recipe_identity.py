"""Public synthetic recipe attribution/default/import policy tests."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import recipe_identity as identity
import recipe_packages as packages
import recipe_catalog
from opsfeast import ConfigError, read_yaml, REPOSITORY_RECIPES


class IdentityTests(unittest.TestCase):
    def test_unknown_defaults_and_custom_copy_without_rewrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.assertEqual(identity.defaults(root),identity.UNKNOWN)
            self.assertFalse((root/identity.DEFAULT_FILE).exists())
            config={'schema_version':1,'recipe_defaults':{'author':{'name':'Fixture author','contacts':['https://example.invalid/contact']},'license':'MIT'}}
            path=root/identity.DEFAULT_FILE
            path.write_text(json.dumps(config))
            original=path.read_bytes()
            defaults=identity.defaults(root)
            defaults['author']['contacts'].append('other')
            self.assertEqual(identity.defaults(root),config['recipe_defaults'])
            self.assertEqual(path.read_bytes(),original)
            config['recipe_defaults']['author']['name']='bUnDlE'
            path.write_text(json.dumps(config))
            with self.assertRaises(ConfigError):identity.defaults(root)

    def test_reserved_author_contacts_case_and_location(self):
        with tempfile.TemporaryDirectory() as directory:
            for author in ({'name':'Bundle','contacts':['contact']},{'name':'Someone','contacts':[' bUnDlE ']},):
                metadata={'author':author,'license':'MIT'}
                with self.assertRaises(ConfigError):identity.validate(metadata,Path(directory))
                with self.assertRaises(ConfigError):identity.validate(metadata,external=True)
            for metadata in ({'author':{'name':'x','contacts':'x'}},{'license':''},{'author':{'name':'x','contacts':[]}}):
                with self.assertRaises(ConfigError):identity.validate(metadata,external=True)

    def test_all_builtin_descriptors_have_exact_bundle_mit(self):
        for name in identity.BUNDLED:
            path=REPOSITORY_RECIPES/name
            descriptor=read_yaml(path/'recipe.yaml')
            self.assertEqual(identity.validate(descriptor,path),{'author':{'name':'Bundle','contacts':['Bundle']},'license':'MIT'})
            self.assertIn('Permission is hereby granted',(path/'LICENSE').read_text())

    def test_bundle_archive_rejected_before_destination_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            item=recipe_catalog.choose(None,'report/summary')
            archive=root/'bundle.zip'
            packages.pack(item,['recipe.yaml','README.md','main.py','LICENSE'],archive)
            with self.assertRaises(ConfigError):packages.unpack(archive,root/'candidate')
            self.assertFalse((root/'candidate').exists())
            with self.assertRaises(ConfigError):packages.pack(item,['recipe.yaml','README.md','main.py'],root/'without-license.zip')
            self.assertFalse((root/'without-license.zip').exists())

    def test_external_import_accepts_unknown_but_rejects_manifest_spoof(self):
        import zipfile,hashlib
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            metadata={'id':'fixture','version':'1','runner':{'entrypoint':'main.py'},'author':{'name':'Fixture','contacts':['Unknown']},'license':'Unknown'}
            payloads={'recipe.yaml':json.dumps(metadata).encode(),'README.md':b'fixture','main.py':b'VERSION="1"\n'}
            manifest={'format':'opsfeast-recipe-bundle','version':'0.1.0','recipe_id':'fixture','recipe_version':'1','author':metadata['author'],'license':'Unknown',
                      'files':{name:{'size_bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in payloads.items()}}
            def save(path):
                with zipfile.ZipFile(path,'w') as z:
                    z.writestr('MANIFEST.json',json.dumps(manifest))
                    for name,data in payloads.items():z.writestr('recipe/'+name,data)
            good=root/'good.zip';save(good)
            packages.unpack(good,root/'accepted')
            manifest['author']={'name':'Bundle','contacts':['Bundle']}
            bad=root/'bad.zip';save(bad)
            with self.assertRaises(ConfigError):packages.unpack(bad,root/'rejected')
            self.assertFalse((root/'rejected').exists())
