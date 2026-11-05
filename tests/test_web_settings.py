"""Persistent per-checkout endpoints; synthetic loopback reservations only."""
from pathlib import Path
import tempfile
import unittest
from opsfeast import ConfigError,load_profiles,save_profiles
from opsfeast.web_settings import read_port,configure_port,bind_server
from opsfeast.core import Instance


class WebSettingsTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)

    def test_first_allocation_is_saved_reserved_and_independent(self):
        self.assertIsNone(read_port(self.root))
        a=bind_server(self.root);self.addCleanup(a.close)
        a.listen();first=a.getsockname()[1]
        self.assertEqual(read_port(self.root),first)
        other=self.root/'other';other.mkdir()
        b=bind_server(other);self.addCleanup(b.close)
        self.assertNotEqual(first,b.getsockname()[1])
        with self.assertRaises(OSError):bind_server(self.root)
        self.assertEqual(read_port(self.root),first)
        a.close()
        again=bind_server(self.root);self.addCleanup(again.close)
        self.assertEqual(again.getsockname()[1],first)

    def test_explicit_setting_and_profile_updates_preserve_each_other(self):
        save_profiles(dict(schema_version=2,default_profile='lab',profiles={'lab':{'root':'feasts/lab'}}),self.root)
        (self.root/'feasts/lab').mkdir(parents=True)
        (self.root/'feasts/lab/hosts.yaml').write_text('hosts: {}\n')
        configure_port(self.root,18741)
        before=load_profiles(self.root)
        self.assertEqual(before['profiles'],{'lab':{'root':'feasts/lab'}})
        Instance.open(self.root).profiles.use('lab')
        self.assertEqual(read_port(self.root),18741)
        self.assertEqual(load_profiles(self.root),before)

    def test_invalid_values_and_unknown_web_fields_do_not_get_repaired(self):
        for value in (True,None,0,80,65536,'8741'):
            with self.assertRaises(ConfigError):configure_port(self.root,value)
        for web in ({},{'port':True},{'port':18741,'surprise':1}):
            save_profiles(dict(schema_version=2,default_profile=None,profiles={},web=web),self.root)
            before=(self.root/'.opsfeast.yaml').read_bytes()
            with self.assertRaises(ConfigError):read_port(self.root)
            self.assertEqual((self.root/'.opsfeast.yaml').read_bytes(),before)

    def test_occupied_explicit_port_does_not_replace_saved_setting(self):
        configure_port(self.root,18741)
        other=self.root/'other';other.mkdir()
        busy=bind_server(other);self.addCleanup(busy.close);busy.listen()
        with self.assertRaises(OSError):bind_server(self.root,busy.getsockname()[1])
        self.assertEqual(read_port(self.root),18741)
