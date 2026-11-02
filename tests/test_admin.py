"""Synthetic credentials only; no real administrator is provisioned by tests."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from opsfeast import admin,ConfigError
from opsfeast.site import SiteConflict


class AdminTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'.opsfeast-data.json').write_text('{"schema_version":"0.1.0","kind":"opsfeast-installation-data"}')

    def test_no_defaults_and_passwords_are_salted_not_plaintext(self):
        self.assertFalse(admin.status(self.root)['configured'])
        self.assertFalse((self.root/admin.FILENAME).exists())
        password='Synthetic-test-password-001'
        first=admin.configure(self.root,username='synthetic',password=password,expected_revision=0)
        raw=(self.root/admin.FILENAME).read_text()
        self.assertNotIn(password,raw)
        self.assertNotIn('digest',first)
        self.assertTrue(admin.verify(self.root,'synthetic',password))
        self.assertFalse(admin.verify(self.root,'unknown',password))
        self.assertFalse(admin.verify(self.root,'synthetic','wrong'))
        self.assertFalse(admin.verify(self.root,'synthetic','\ud800'*12))
        salt=json.loads(raw)['salt']
        admin.configure(self.root,username='synthetic2',password=password,current_password=password,expected_revision=1)
        self.assertNotEqual(json.loads((self.root/admin.FILENAME).read_text())['salt'],salt)
        self.assertTrue(admin.verify(self.root,'synthetic2',password))

    def test_unicode_passwords_preserve_exact_text_and_code_point_limits(self):
        password='  維運基地中文密碼🦉e\u0301  '
        admin.configure(self.root,username='synthetic',password=password,expected_revision=0)
        self.assertTrue(admin.verify(self.root,'synthetic',password))
        self.assertFalse(admin.verify(self.root,'synthetic',password.strip()))
        import unicodedata
        self.assertFalse(admin.verify(self.root,'synthetic',unicodedata.normalize('NFC',password)))
        self.assertNotIn(password,(self.root/admin.FILENAME).read_text())
        replacement='🦉'*256
        admin.configure(self.root,username='synthetic',password=replacement,current_password=password,expected_revision=1)
        self.assertTrue(admin.verify(self.root,'synthetic',replacement))
        with self.assertRaises(ConfigError):
            admin.configure(self.root,username='synthetic',password='🦉'*257,current_password=replacement,expected_revision=2)

    def test_conflict_and_current_password_preserve_existing_account(self):
        admin.configure(self.root,username='synthetic',password='Synthetic-test-password-001',expected_revision=0)
        for revision,error in [(0,SiteConflict),(1,admin.InvalidCredentials)]:
            with self.assertRaises(error):admin.configure(self.root,username='other',password='Synthetic-test-password-002',current_password='wrong',expected_revision=revision)
        self.assertEqual(admin.status(self.root)['username'],'synthetic')
        for username,password in [('x','Synthetic-test-password-001'),('valid','short'),('valid','\ud800'*12)]:
            with self.assertRaises(ConfigError):admin.configure(self.root,username=username,password=password,expected_revision=1)

    def test_corrupt_metadata_is_not_treated_as_unconfigured(self):
        (self.root/admin.FILENAME).write_text('{}')
        with self.assertRaises(ConfigError):admin.status(self.root)

    def test_cli_password_input_is_private_and_noninteractive_requires_opt_in(self):
        prefix=[sys.executable,'-B','-m','opsfeast.settings','admin','set','--data-root',str(self.root),'--username','synthetic','--expected-revision','0']
        result=subprocess.run(prefix,input='',capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        password='Synthetic-test-password-001'
        result=subprocess.run(prefix+['--password-stdin'],input=json.dumps({'password':password}),capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotIn(password,result.stdout+result.stderr)
        self.assertTrue(admin.verify(self.root,'synthetic',password))


if __name__=='__main__':unittest.main()
