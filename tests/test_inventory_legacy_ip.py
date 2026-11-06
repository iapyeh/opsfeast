"""Synthetic old-iproute2 support with original failure evidence preserved."""
import runpy
from pathlib import Path
from types import SimpleNamespace
import unittest
from inventory_output_fixture import framed
import test_inventory_jobs as fixtures

ROOT=Path(__file__).resolve().parents[1]
DETAILS=runpy.run_path(str(ROOT/'recipes/system/inventory/overview/details.py'))
JOBS=runpy.run_path(str(ROOT/'recipes/system/inventory/overview/jobs.py'))
ADDRESS='''1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
2: eth0@if7: <BROADCAST,MULTICAST,UP> mtu 1500 qdisc mq state UP group default
    link/ether 02:00:00:00:00:01 brd ff:ff:ff:ff:ff:ff
    inet 192.0.2.8/24 brd 192.0.2.255 scope global eth0
    inet6 2001:db8::8/64 scope global
3: eth1: <BROADCAST,MULTICAST> mtu 1500 qdisc noop state DOWN group default
    link/ether 02:00:00:00:00:02 brd ff:ff:ff:ff:ff:ff
'''

class OldIP(fixtures.Actor):
    error='Option "-j" is unknown, try "ip -help".\r\n'
    text=ADDRESS
    def exec_command(self,argv,**options):
        script=argv[-1]
        if 'ip -j ' in script:
            self.commands.append(script)
            return SimpleNamespace(stdout=framed(script,'\n__OPSFEAST_EXIT_255\n',self.error),stderr='',exitcode=0)
        if 'LC_ALL=C ip ' in script:
            self.commands.append(script)
            output=self.text if 'address show' in script else 'default via 192.0.2.1 dev eth0\n'
            return SimpleNamespace(stdout=framed(script,output+'\n__OPSFEAST_EXIT_0\n'),stderr='',exitcode=0)
        return super().exec_command(argv,**options)

class LegacyIPTests(unittest.TestCase):
    def collect(self,actor):
        return JOBS['collect'](actor,'synthetic',['network-configuration','network-state'],
            properties=['network.ipv4.address','network.ipv6.address','network.interfaces.name','network.routes'])

    def test_old_ip_support_retains_failed_json_and_successful_text_sources(self):
        result=self.collect(OldIP())
        samples=[s for g in result['groups'] for s in g['samples']]
        self.assertIn('192.0.2.8',[s['value'] for s in samples])
        self.assertIn('2001:db8::8',[s['value'] for s in samples])
        self.assertTrue(all(s['status']=='success' for s in samples))
        probes=result['probes'];by_id={p['id']:p for p in probes}
        self.assertEqual(len([p for p in probes if p.get('exitcode')==255]),2)
        for sample in samples:
            self.assertEqual(by_id[sample['source_id']]['status'],'success')
        routes=next(s['value'] for s in samples if s['property']=='network.routes')
        self.assertEqual(routes,[{'entry':'default via 192.0.2.1 dev eth0'}])
        from opsfeast.host_reference import from_interfaces
        candidate=from_interfaces(DETAILS['linux_text_interfaces'](ADDRESS),'2026-11-06T00:00:00Z','text')
        self.assertEqual(candidate['ipv4_addresses'],['192.0.2.8'])
        self.assertEqual(candidate['ipv6_addresses'],['2001:db8::8'])

    def test_permission_failure_does_not_trigger_another_command(self):
        actor=OldIP();actor.error='Permission denied\n'
        result=self.collect(actor)
        self.assertFalse(any('LC_ALL=C ip ' in cmd for cmd in actor.commands))
        self.assertTrue(all(s['status']=='unavailable' for g in result['groups'] for s in g['samples']))

    def test_malformed_text_is_not_success_or_an_empty_ip_list(self):
        actor=OldIP();actor.text='unexpected output\n'
        result=self.collect(actor)
        addresses=[s for g in result['groups'] for s in g['samples'] if s['property']=='network.ipv4.address']
        self.assertTrue(all(s['status']=='unavailable' for s in addresses))
        for text in ('','2: malformed\n',ADDRESS.replace('192.0.2.8/24','bad/24')):
            with self.subTest(text=text),self.assertRaises(ValueError):DETAILS['linux_text_interfaces'](text)
