"""Synthetic lsblk capability selection; no host connections or package installs."""
from types import SimpleNamespace
import unittest
from inventory_output_fixture import framed
from test_inventory_legacy_ip import DETAILS,JOBS
import test_inventory_jobs as fixtures

PAIRS=r'''NAME="sda" TYPE="disk" SIZE="1073741824" FSTYPE="" MOUNTPOINT="" MODEL="Virtual\x20Disk"
NAME="sda1" TYPE="part" SIZE="536870912" FSTYPE="ext4" MOUNTPOINT="/srv/with\x20space" MODEL=""
'''

class OldLSBLK(fixtures.Actor):
    error="lsblk: invalid option -- 'J'\r\n"
    pairs=PAIRS
    def exec_command(self,argv,**options):
        script=argv[-1]
        if 'lsblk -b -J ' in script:
            self.commands.append(script)
            return SimpleNamespace(stdout=framed(script,'\n__OPSFEAST_EXIT_1\n',self.error),stderr='',exitcode=0)
        if 'lsblk -b -P ' in script:
            self.commands.append(script)
            return SimpleNamespace(stdout=framed(script,self.pairs+'\n__OPSFEAST_EXIT_0\n'),stderr='',exitcode=0)
        return super().exec_command(argv,**options)

class LegacyLSBLKTests(unittest.TestCase):
    def collect(self,actor):
        return JOBS['collect'](actor,'synthetic',['storage-layout'],properties=[
            'storage.block_devices.name','storage.block_devices.size','storage.block_devices.mountpoint'])

    def test_pairs_and_original_failed_attempt_are_preserved(self):
        actor=OldLSBLK();result=self.collect(actor)
        samples=result['groups'][0]['samples'];by_id={p['id']:p for p in result['probes']}
        self.assertIn(1073741824,[s['value'] for s in samples])
        self.assertIn('/srv/with space',[s['value'] for s in samples])
        self.assertTrue(all(by_id[s['source_id']]['command'].startswith('LC_ALL=C lsblk') for s in samples))
        self.assertTrue(any(p['exitcode']==1 and p['stderr']==actor.error for p in result['probes']))
        rows=DETAILS['linux_pair_devices'](PAIRS)
        self.assertEqual(rows[0]['model'],'Virtual Disk')
        self.assertIsNone(rows[0]['fstype'])
        self.assertIsNone(rows[0]['mountpoint'])
        self.assertEqual(DETAILS['linux_pair_devices'](PAIRS.replace('Virtual\\x20Disk',r'\\xe6\\xb8\\xac'))[0]['model'],'測')

    def test_permission_failure_is_not_retried_and_bad_pairs_stay_gaps(self):
        actor=OldLSBLK();actor.error='permission denied\n'
        result=self.collect(actor)
        self.assertFalse(any('lsblk -b -P ' in c for c in actor.commands))
        self.assertTrue(all(s['status']=='unavailable' for s in result['groups'][0]['samples']))
        actor=OldLSBLK();actor.pairs='NAME="sda" SIZE="unknown"'
        result=self.collect(actor)
        self.assertTrue(all(s['status']=='unavailable' for s in result['groups'][0]['samples']))

    def test_empty_duplicate_missing_and_invalid_size_are_rejected(self):
        for value in ('',PAIRS.replace('SIZE="1073741824"','SIZE="-1"'),
                      PAIRS.replace('TYPE="disk"','NAME="duplicate"'),
                      PAIRS.replace('MODEL="Virtual\\x20Disk"','')):
            with self.subTest(value=value),self.assertRaises(ValueError):DETAILS['linux_pair_devices'](value)
