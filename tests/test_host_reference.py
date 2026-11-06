"""Reference addresses: synthetic saved-collection integration and read-only APIs."""
from contextlib import redirect_stdout, redirect_stderr
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from opsfeast import ConfigError, main
from opsfeast.host_reference import from_interfaces, read, update, esxi_ipv4_interfaces, refresh_from_saved
import hosts_cli
import inventory_jobs as service
import retention_replay as replay
import test_inventory_jobs as fixtures
Actor = fixtures.Actor

ESXI_TABLE = 'Name  IPv4 Address  IPv4 Netmask  IPv4 Broadcast  Address Type  Gateway  DHCP DNS\n----  ------------  ------------  --------------  ------------  -------  --------\nvmk0  192.0.2.42  255.255.255.0  192.0.2.255  STATIC  192.0.2.1  false\n'

class EsxiActor(Actor):
    def exec_command(self, argv, **kwargs):
        from inventory_output_fixture import framed
        result = super().exec_command(argv, **kwargs)
        if 'uname -s' in argv[-1]: result.stdout = result.stdout.replace('Linux', 'VMkernel')
        if 'esxcli network ip interface ipv4 get' in argv[-1]:
            result.stdout = framed(argv[-1], ESXI_TABLE + '\n__OPSFEAST_EXIT_0\n')
        return result


class HostReferenceTests(unittest.TestCase):
    setUp = fixtures.InventoryJobTests.setUp
    enable = fixtures.InventoryJobTests.enable
    acquire = fixtures.InventoryJobTests.acquire

    def files(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def test_esxi_ipv4_updates_reference_and_does_not_claim_ipv6_collection(self):
        self.enable()
        raw = self.acquire(EsxiActor(), properties=['network.ipv4.address','network.ipv6.address'], save=True)
        self.assertEqual(raw['platform'],'esxi')
        self.assertEqual(raw['reference_ips_update']['status'],'updated',raw)
        self.assertEqual(read(self.root,'node')['ipv4_addresses'],['192.0.2.42'])
        self.assertEqual(read(self.root,'node')['collected_families'],[4])
        samples=[sample for group in raw['groups'] for sample in group['samples']]
        self.assertTrue(any(s['property']=='network.ipv4.address' and s['value']=='192.0.2.42' for s in samples))
        self.assertTrue(any(s['property']=='network.ipv6.address' and s['reason_code']=='ipv6_not_collected' for s in samples))

    def test_esxi_saved_recovery_verifies_provenance_and_never_rewrites_history(self):
        self.enable()
        with patch('opsfeast.host_reference.from_interfaces',side_effect=ValueError('simulate omitted projection')):
            raw=self.acquire(EsxiActor(),properties=['network.ipv4.address'],save=True)
        self.assertEqual(read(self.root,'node')['status'],'unknown')
        before=self.files()
        with patch.object(service,'collect_host',side_effect=AssertionError('no connection')):
            receipt=refresh_from_saved(self.root,['node'])
        self.assertEqual(receipt['hosts'][0]['status'],'updated',receipt)
        self.assertEqual(read(self.root,'node')['ipv4_addresses'],['192.0.2.42'])
        self.assertEqual(read(self.root,'node')['observed_at'],raw['probes'][1]['observed_at'])
        after=self.files()
        self.assertTrue(all(after[path]==content for path,content in before.items()))

    def test_loopback_is_filtered_on_projection_and_existing_record_reads(self):
        projected=from_interfaces([{'address':'127.0.0.1'},{'address':'127.5.1.2'},{'address':'::1'},{'address':'192.0.2.3'}],'2026-11-05T00:00:00Z','p')
        self.assertEqual(projected['ipv4_addresses'],['192.0.2.3'])
        self.assertEqual(projected['ipv6_addresses'],[])
        self.enable();raw=self.acquire(Actor(),properties=['network.ipv4.address'],save=True)
        path=next((self.root/'.host-reference-ips').glob('*.json'))
        saved=json.loads(path.read_text());saved['ipv4_addresses'].append('127.0.0.1');path.write_text(json.dumps(saved))
        before=path.read_bytes()
        self.assertNotIn('127.0.0.1',read(self.root,'node')['ipv4_addresses'])
        self.assertEqual(path.read_bytes(),before)

    def test_esxi_parser_rejects_invalid_or_incomplete_tables(self):
        self.assertEqual(esxi_ipv4_interfaces(ESXI_TABLE)[0]['prefix_length'],24)
        for text in ('', 'vmk0 192.0.2.1', ESXI_TABLE.replace('192.0.2.42','invalid'), ESXI_TABLE.replace('255.255.255.0','bad-mask')):
            with self.subTest(text=text), self.assertRaises(ValueError):esxi_ipv4_interfaces(text)

    def test_success_failure_unrelated_and_no_save(self):
        self.enable()
        config = (self.root / 'hosts.yaml').read_bytes()
        before = self.files()
        self.assertEqual(read(self.root, 'node')['status'], 'unknown')
        self.assertEqual(self.files(), before)
        actor = Actor()
        first = self.acquire(actor, properties=['network.ipv4.address'], save=True)
        self.assertEqual(first['reference_ips_update']['status'], 'updated', first)
        saved = read(self.root, 'node')
        self.assertEqual(saved['ipv4_addresses'], ['192.0.2.1'])
        # The shared interface probe enumerates both families even for an IPv4 selector.
        self.assertEqual(saved['ipv6_addresses'], ['2001:db8::1'])
        self.assertEqual(saved['source_observation_id'], first['source_observation_id'])
        self.assertEqual(saved['source_record_id'], first['retention']['record_id'])
        self.assertEqual((self.root / 'hosts.yaml').read_bytes(), config)
        self.assertEqual(replay.ingest(self.root, [Path(first['result_path'])])['files'][0]['status'], 'already_stored')
        self.assertEqual(read(self.root, 'node'), saved)
        actor.fail.add('ip -j address')
        failed = self.acquire(actor, properties=['network.ipv4.address'], save=True)
        self.assertEqual(failed['reference_ips_update']['status'], 'skipped')
        self.assertEqual(read(self.root, 'node'), saved)
        self.acquire(Actor(), properties=['system.hostname'], save=True)
        self.assertEqual(read(self.root, 'node'), saved)
        before = self.files()
        unsaved = self.acquire(Actor(), properties=['network.ipv6.address'])
        self.assertEqual(unsaved['reference_ips_update']['reason_code'], 'utility_no_store')
        self.assertEqual(self.files(), before)

    def test_new_addresses_and_successful_empty_replace_old_set(self):
        self.enable()
        self.acquire(Actor(), properties=['network.ipv4.address'], save=True)
        class Changed(Actor):
            def exec_command(self, argv, **kwargs):
                result = super().exec_command(argv, **kwargs)
                result.stdout = result.stdout.replace('192.0.2.1', '192.0.2.99')
                return result
        second = self.acquire(Changed(), properties=['network.interfaces.mac'], save=True)
        self.assertEqual(second['reference_ips_update']['status'], 'updated')
        self.assertEqual(read(self.root, 'node')['ipv4_addresses'], ['192.0.2.99'])
        class Empty(Actor):
            def exec_command(self, argv, **kwargs):
                result = super().exec_command(argv, **kwargs)
                if 'ip -j address' in argv[-1]:
                    start = result.stdout.index('[{')
                    end = json.JSONDecoder().raw_decode(result.stdout[start:])[1] + start
                    result.stdout = result.stdout[:start] + '[]' + result.stdout[end:]
                return result
        third = self.acquire(Empty(), properties=['network.ipv4.address'], save=True)
        self.assertEqual(third['reference_ips_update']['status'], 'updated', third)
        self.assertEqual(read(self.root, 'node')['ipv4_addresses'], [])
        self.assertEqual(read(self.root, 'node')['status'], 'known')

    def test_invalid_rows_and_normalized_families(self):
        result = from_interfaces([{'kind':'ether','address':'02:00:00:00:00:01'},
            {'address':'192.0.2.2'}, {'address':'192.0.2.2'}, {'address':'fe80::1%em0'},
            {'name':'empty','address':None}], '2026-10-30T00:00:00Z', 'probe-1')
        self.assertEqual(result['ipv4_addresses'], ['192.0.2.2'])
        self.assertEqual(result['ipv6_addresses'], ['fe80::1%em0'])
        for row in ({'entry':'unparsed'}, {'address':'invalid'}, 'bad'):
            with self.subTest(row=row), self.assertRaises(ValueError):
                from_interfaces([row], '2026-10-30T00:00:00Z', 'probe-1')

    def test_reference_update_error_is_visible_and_preserves_previous(self):
        self.enable()
        self.acquire(Actor(), properties=['network.ipv4.address'], save=True)
        previous = read(self.root, 'node')
        with patch('opsfeast.host_reference.update', side_effect=OSError('private detail')):
            result = self.acquire(Actor(), properties=['network.ipv4.address'], save=True)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(service.result_exit_code(result), 1)
        self.assertEqual(result['retention']['status'], 'stored')
        self.assertEqual(result['reference_ips_update']['status'], 'failed')
        self.assertNotIn('private detail', json.dumps(result))
        self.assertEqual(read(self.root, 'node'), previous)

    def test_old_concurrent_result_and_failed_retention_cannot_overwrite(self):
        self.enable()
        result = self.acquire(Actor(), properties=['network.ipv4.address'], save=True)
        previous = read(self.root, 'node')
        older = copy.deepcopy(result)
        older['reference_ips']['observed_at'] = '2000-01-01T00:00:00Z'
        self.assertEqual(update(self.root, older)['reason_code'], 'newer_success_already_saved')
        result['retention']['status'] = 'failed'
        self.assertEqual(update(self.root, result)['reason_code'], 'retention_not_stored')
        self.assertEqual(read(self.root, 'node'), previous)

    def test_successful_interfaces_survive_other_probe_failures(self):
        self.enable()
        actor = Actor()
        actor.fail.add('df -Pk')
        result = self.acquire(actor, properties=['network.ipv4.address','storage.filesystems.used_percent'], save=True)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['reference_ips_update']['status'], 'updated')
        self.assertEqual(read(self.root, 'node')['ipv4_addresses'], ['192.0.2.1'])

    def test_invalid_address_collection_preserves_reference(self):
        self.enable()
        self.acquire(Actor(), properties=['network.ipv4.address'], save=True)
        previous = read(self.root, 'node')
        class Invalid(Actor):
            def exec_command(self, argv, **kwargs):
                result = super().exec_command(argv, **kwargs)
                result.stdout = result.stdout.replace('192.0.2.1', 'invalid-address')
                return result
        result = self.acquire(Invalid(), properties=['network.interfaces.mac'], save=True)
        self.assertEqual(result['reference_ips_update']['status'], 'skipped')
        self.assertEqual(read(self.root, 'node'), previous)

    def test_recipe_summary_preserves_reference_update_failure(self):
        import recipe_runner
        from recipe_test_support import recipe_main
        result = {'status':'success', 'reference_ips_update':{'status':'failed'}}
        self.assertEqual(recipe_runner.execution_exit_code([result]), 1)
        from retention_replay import raw_digest
        self.assertEqual(raw_digest(result), raw_digest(dict(result, reference_ips_update={'status':'updated'})))
        with patch.object(service, 'collect_host', return_value=dict(result, result_path=None)), redirect_stdout(io.StringIO()) as output:
            code = recipe_main(['system/inventory/overview','--host','node','--root',str(self.root),'--json'])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue())['reference_ips_update']['status'], 'failed')

    def test_core_cli_reads_are_independent_of_retention_and_do_not_connect(self):
        self.enable()
        self.acquire(Actor(), properties=['network.ipv4.address'], save=True)
        before = self.files()
        with patch.object(service, 'collect_host', side_effect=AssertionError('no collection')):
            host_api = service.profile(self.root).hosts
            self.assertEqual(host_api.reference_ips('node')['ipv4_addresses'], ['192.0.2.1'])
            with self.assertRaises(ConfigError): host_api.reference_ips('absent')
            for command in (['list'], ['show', 'node']):
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(main(['hosts', *command, '--root', str(self.root), '--json']), 0)
                self.assertEqual(json.loads(output.getvalue())['hosts'][0]['host_id'], 'node')
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(hosts_cli.main(['show','absent','--root',str(self.root),'--json']), 1)
        self.assertEqual(self.files(), before)

    def test_unknown_hosts_in_list_and_table_and_help(self):
        with patch('hosts_cli.resolve_root', side_effect=AssertionError('help must not load profile')):
            for command in ([], ['list'], ['show']):
                with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as exc:
                    main(['hosts', *command, '--help'])
                self.assertEqual(exc.exception.code, 0)
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(['hosts','list','--root',str(self.root),'--json']), 0)
        self.assertEqual(json.loads(output.getvalue())['hosts'][0]['reference_ips']['status'], 'unknown')
        output = io.StringIO()
        with redirect_stdout(output), patch.object(output, 'isatty', return_value=True):
            self.assertEqual(main(['hosts','list','--root',str(self.root)]), 0)
        self.assertIn('unknown', output.getvalue())

    def test_reference_paths_reject_symlinks(self):
        (self.root / '.host-reference-ips').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ConfigError): read(self.root, 'node')

    def test_malformed_reference_is_reported_without_replacement(self):
        from opsfeast.host_reference import _path
        path = _path(self.root, 'node')
        path.parent.mkdir()
        path.write_text('[]')
        with self.assertRaises(ConfigError): read(self.root, 'node')
