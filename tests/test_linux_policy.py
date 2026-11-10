"""Fixed-query policy projections and portable recipe delivery; synthetic targets."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from opsfeast import ConfigError, Instance, read_yaml
from opsfeast.data_contract import validate
from opsfeast import linux_policy_probe as probe, linux_profile as service
from opsfeast.linux_policy_schema import DATASETS, schema
from opsfeast.profiling import inspect_host
from test_core_api import Actor, Result
import test_host_vault as fixtures

ROOT = Path(__file__).resolve().parents[1]
SECRET = 'SYNTHETIC_SECRET_MUST_NOT_BE_RETAINED'
REFERENCES = {
    'ssh-policy': 'system/access/inventory/ssh-policy',
    'sudo-policy': 'system/account/inventory/sudo-policy',
    'firewall-policy': 'system/network/inventory/firewall-policy',
    'time-sync': 'system/time/inventory/synchronization',
    'logging-config': 'system/logging/inventory/configuration',
}


def files(root):
    contents = {
        'etc/systemd/journald.conf': '[Journal]\nStorage=persistent\nSystemMaxUse=1G\n# password=' + SECRET,
        'etc/systemd/journald.conf.d/limit.conf': '[Journal]\nMaxRetentionSec=7day\n',
        'etc/rsyslog.conf': '$IncludeConfig /etc/rsyslog.d/*.conf\n*.info /var/log/syslog\n',
        'etc/rsyslog.d/forward.conf': 'action(type="omfwd" target="192.0.2.30" port="6514" protocol="tcp" password="' + SECRET + '")\n',
        'etc/nginx/nginx.conf': 'include conf.d/*.conf;\nerror_log /var/log/nginx/error.log warn;\n',
        'etc/nginx/conf.d/site.conf': 'access_log /var/log/nginx/access.log combined;\nproxy_set_header Authorization "' + SECRET + '";\n',
        'etc/my.cnf': '[client]\npassword=' + SECRET + '\n[mysqld]\nlog_error=/var/log/mysql/error.log\nslow_query_log=1\n',
        'etc/logrotate.conf': 'include /etc/logrotate.d\nweekly\n',
        'etc/logrotate.d/nginx': '/var/log/nginx/*.log {\ndaily\nrotate 7\ncompress\npostrotate\ncurl --password ' + SECRET + '\nendscript\n}\n',
        'etc/chrony.conf': 'server 192.0.2.10 iburst key ' + SECRET + '\nmakestep 1.0 3\n',
        'etc/systemd/timesyncd.conf': '[Time]\nNTP=192.0.2.10\n',
    }
    for name, text in contents.items():
        path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text)


def fake_run(argv, deadline):
    cmd = tuple(argv)
    out = ''
    if argv[:2] == ['sshd', '-T']:
        out = 'port 22\npermitrootlogin no\npasswordauthentication no\nallowusers operator\nauthorizedkeyscommand ' + SECRET + '\n'
    elif argv[0] == 'sudo':
        out = 'Matching Defaults entries for operator:\n    env_file=' + SECRET + '\n\nSudoers entry:\n    RunAsUsers: root\n    Options: !authenticate\n    Commands:\n        /usr/bin/systemctl status nginx ' + SECRET + '\n        ALL\n'
    elif argv[0] == 'nft':
        out = json.dumps({'nftables':[{'table':{'family':'inet','name':'filter'}},
            {'chain':{'family':'inet','table':'filter','name':'input','policy':'drop'}},
            {'rule':{'family':'inet','table':'filter','chain':'input','expr':[{'accept':None},{'log':{'prefix':SECRET}}], 'comment':SECRET}}]})
    elif argv[0] in ('iptables-save', 'ip6tables-save'):
        out = '*filter\n:INPUT DROP [0:0]\n-A INPUT -p tcp --dport 22 -m comment --comment "' + SECRET + '" -j ACCEPT\nCOMMIT\n'
    elif argv[0] == 'firewall-cmd': out = 'public (active)\n  interfaces: eth0\n  ports: 22/tcp\n'
    elif argv[0] == 'ufw': out = 'Status: active\nDefault: deny (incoming), allow (outgoing)\n22/tcp ALLOW IN Anywhere # ' + SECRET + '\n'
    elif cmd[:2] == ('timedatectl', 'show'):
        out = 'Timezone=Asia/Taipei\nLocalRTC=no\nNTP=yes\nNTPSynchronized=no\nTimeUSec=1000\nRTCTimeUSec=900\n'
    elif cmd[:2] == ('timedatectl', 'show-timesync'): out = 'ServerName=ntp.example\nServerAddress=192.0.2.10\nFrequency=12\n'
    elif argv[:3] == ['chronyc','-n','tracking']: out = 'Reference ID : C000020A (192.0.2.10)\nStratum : 3\nLast offset : 0.0001 seconds\nLeap status : Normal\n'
    elif argv[:3] == ['chronyc','-n','sources']: out = 'MS Name/IP address Stratum Poll Reach LastRx Last sample\n===============================================================================\n^* 192.0.2.10 2 6 377 20 +10us[+11us] +/- 1ms\n'
    elif argv[:2] == ['ntpq','-pn']: out = 'remote refid st t when poll reach delay offset jitter\n==============================================================================\n*192.0.2.10 .GPS. 1 u 20 64 377 1.0 0.1 0.2\n'
    elif argv[0] == 'ntpq': out = 'associd=0 status=0615 leap_none, stratum=3, offset=0.01, frequency=12\n'
    elif argv[0] == 'journalctl': out = 'Archived and active journals take up 24.0M in the file system.\n'
    else: raise AssertionError(argv)
    stamp = probe.now()
    return out, '', {'argv':argv, 'started_at':stamp, 'completed_at':stamp, 'exitcode':0,
                     'termination_status':'confirmed','reason_code':None}


def snapshot(root, kind, **kwargs):
    with patch.object(probe, 'run', side_effect=fake_run), patch.object(probe.os, 'geteuid', return_value=1000):
        return probe.snapshot(kind, kwargs.pop('limit', 1000), 5, root=root, **kwargs)


class LinuxPolicyTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        self.root = Path(directory.name); files(self.root)

    def test_all_five_kinds_are_schema_bound_and_keep_no_fixture_secrets(self):
        self.assertEqual(DATASETS, probe.DATASETS)
        for kind in DATASETS:
            data = snapshot(self.root, kind); validate(data, schema(kind, acquisition=False))
            self.assertNotIn(SECRET, json.dumps(data), kind)
            self.assertEqual(data['effective_uid'], 1000)
            self.assertEqual(set(data['datasets']), set(DATASETS[kind]))

    def test_ssh_context_global_and_selected_policy_are_distinct(self):
        context = {'user':'operator','host':'client.example','addr':'192.0.2.5','laddr':'192.0.2.2','lport':22}
        global_data = snapshot(self.root, 'ssh-policy')['datasets']['ssh_policy']
        effective = snapshot(self.root, 'ssh-policy', options=context)['datasets']['ssh_policy']
        self.assertEqual(global_data['items'][0]['basis'], 'configured')
        self.assertEqual(effective['items'][0]['basis'], 'effective')
        self.assertIn('-C', effective['commands'][0]['argv'])
        self.assertEqual(effective['items'][-1]['value']['addr'], '192.0.2.5')
        for invalid in ({'user':'operator'}, {**context,'user':'x,addr=evil'}, {**context,'addr':'not-ip'}, {**context,'addr':1}, {**context,'addr':'fe80::1%zone,user=root'}, {**context,'lport':True}):
            with self.assertRaises(ValueError): probe.context(invalid)

    def test_sudo_lists_actor_without_executing_commands_and_marks_lossy_details(self):
        data = snapshot(self.root, 'sudo-policy')['datasets']['sudo_policy']
        self.assertEqual(data['commands'][0]['argv'], ['sudo','-n','-ll'])
        self.assertFalse(data['complete'])
        self.assertIn('sudo_arguments_omitted', data['reason_codes'])
        self.assertIn('sudo_defaults_not_projected', data['reason_codes'])
        entry = data['items'][0]['value']
        self.assertEqual(entry['run_as_users'], ['root'])
        self.assertEqual(entry['commands'][0], {'executable':'/usr/bin/systemctl','arguments_omitted':True})
        self.assertIn('!authenticate', entry['options'])

    def test_firewall_native_backends_and_runtime_permanent_scope(self):
        data = snapshot(self.root, 'firewall-policy')['datasets']
        self.assertIn('firewall_text_omitted', data['nft_rules']['reason_codes'])
        self.assertIn('firewall_text_omitted', data['iptables_rules']['reason_codes'])
        self.assertTrue(data['firewalld_runtime']['complete'])
        self.assertEqual(data['firewalld_runtime']['items'][0]['basis'], 'runtime')
        self.assertEqual(data['firewalld_permanent']['items'][0]['basis'], 'configured')
        self.assertIn('drop', json.dumps(data['nft_rules']))
        def malformed(argv, deadline):
            _, err, evidence = fake_run(argv, deadline)
            return ('not json' if argv[0]=='nft' else '*filter\n:INPUT DROP [0:0]\n' if argv[0].endswith('tables-save') else ''), err, evidence
        with patch.object(probe, 'run', malformed):
            result = probe.firewall(time.monotonic()+5, 1000)
        self.assertFalse(result['nft_rules']['complete'])
        self.assertFalse(result['iptables_rules']['complete'])

    def test_time_sync_reports_unsynchronized_and_sources_without_changing_clock(self):
        data = snapshot(self.root, 'time-sync')['datasets']
        values = {i['name']:i['value'] for i in data['clock_state']['items']}
        self.assertEqual(values['NTPSynchronized'], 'no')
        self.assertTrue(data['clock_state']['complete'])  # query completeness, not synchronization health
        self.assertTrue(data['chrony_sources']['items'])
        self.assertTrue(data['ntp_peers']['items'])
        self.assertIn('configuration_fields_omitted', data['time_configuration']['reason_codes'])
        self.assertNotIn(SECRET, json.dumps(data))
        for section in data.values():
            for command in section['commands']:
                self.assertFalse(any('set-' in arg or arg in ('makestep','burst') for arg in command['argv']))

    def test_logging_projection_never_reads_log_contents_or_retains_scripts_passwords(self):
        data = snapshot(self.root, 'logging-config')['datasets']
        text = json.dumps(data)
        for expected in ('/var/log/syslog','/var/log/nginx/access.log','/var/log/mysql/error.log','MaxRetentionSec','rotate'):
            self.assertIn(expected, text)
        self.assertNotIn(SECRET, text); self.assertNotIn('curl', text)
        self.assertEqual(data['journal_state']['commands'][0]['argv'], ['journalctl','--disk-usage','--no-pager'])
        self.assertIn('syslog_partial_projection', data['syslog_configuration']['reason_codes'])

    def test_includes_are_bounded_and_outside_symlinks_are_not_read(self):
        outside = self.root / 'private.conf'; outside.write_text('*.info /secret-location-' + SECRET)
        (self.root / 'etc/rsyslog.d/escape.conf').symlink_to(outside)
        data = snapshot(self.root, 'logging-config')['datasets']['syslog_configuration']
        self.assertIn('include_outside_scope', data['reason_codes']); self.assertNotIn(SECRET, json.dumps(data))
        (self.root / 'etc/nginx/conf.d/site.conf').write_text('include /etc/nginx/nginx.conf;\naccess_log /safe.log;\n')
        data = snapshot(self.root, 'logging-config')['datasets']['application_logs']
        self.assertLess(data['attempted_count'], 10)
        with patch.object(probe, 'MAX_FILES', 1): data = snapshot(self.root, 'logging-config')
        self.assertIn('file_limit', json.dumps(data))
        with patch.object(probe, 'MAX_FILE', 5): data = snapshot(self.root, 'logging-config')
        self.assertIn('file_size_limit', json.dumps(data))

    def test_inline_scripts_and_sensitive_routing_fields_are_not_emitted(self):
        data = probe.section('fixture','configured')
        probe.rotation_parser('/safe/log { postrotate echo ' + SECRET + '; }', '/etc/logrotate.conf', data, 100)
        self.assertNotIn(SECRET, json.dumps(data)); self.assertFalse(data['complete'])
        probe.application_parser('server { access_log /a; error_log /b; }', '/etc/nginx/nginx.conf', data, 100)
        self.assertIn('unrecognized_configuration', data['reason_codes'])
        probe.syslog_parser('action(type="omhttp" target="https://user:' + SECRET + '@example/path")', '/etc/rsyslog.conf', data, 100)
        probe.syslog_parser('*.info @@user:' + SECRET + '@example', '/etc/rsyslog.conf', data, 100)
        self.assertNotIn(SECRET, json.dumps(data))
        def variant(argv, deadline):
            out, err, evidence = fake_run(argv, deadline)
            if argv[0] in ('iptables-save','ip6tables-save'):
                out = '*filter\n-A INPUT --comment=' + SECRET + ' -j ACCEPT\nCOMMIT\n'
            elif argv[0] == 'firewall-cmd':
                out = "public\n  rich rules: log prefix='test " + SECRET + "'\n"
            return out, err, evidence
        with patch.object(probe,'run',variant):
            self.assertNotIn(SECRET,json.dumps(probe.firewall(time.monotonic()+5,1000)))

    def test_missing_tools_warnings_output_and_item_limits_remain_gaps(self):
        def missing(argv, deadline):
            stamp=probe.now()
            return SECRET, SECRET, {'argv':argv,'started_at':stamp,'completed_at':stamp,'exitcode':None,
                'termination_status':'not_started','reason_code':'tool_missing'}
        with patch.object(probe,'run',missing): data=probe.snapshot('firewall-policy',100,5,root=self.root)
        self.assertNotIn(SECRET,json.dumps(data))
        self.assertTrue(all(not d['complete'] and not d['items'] for d in data['datasets'].values()))
        limited=snapshot(self.root,'logging-config',limit=1)
        self.assertIn('item_limit',json.dumps(limited))
        with patch.object(probe,'MAX_OUTPUT',2500): limited=snapshot(self.root,'logging-config')
        self.assertIn('output_size_limit',json.dumps(limited))

    def test_command_runner_is_bounded_reaps_its_process_and_does_not_retain_streams(self):
        out, err, evidence=probe.run([sys.executable,'-c','print("fixture")'],time.monotonic()+2)
        self.assertEqual(out.strip(),'fixture');self.assertEqual(evidence['termination_status'],'confirmed')
        _, _, evidence=probe.run([sys.executable,'-c','import time; time.sleep(5)'],time.monotonic()+.1)
        self.assertEqual(evidence['reason_code'],'time_limit');self.assertEqual(evidence['termination_status'],'confirmed')
        with patch.object(probe,'MAX_CAPTURE',1024):
            _, _, evidence=probe.run([sys.executable,'-c','print("x"*100000)'],time.monotonic()+2)
        self.assertEqual(evidence['reason_code'],'command_output_limit')
        with patch.object(probe.shutil,'which',return_value=None):
            _, _, evidence=probe.run(['missing-tool'],time.monotonic()+2)
        self.assertEqual(evidence['reason_code'],'tool_missing');self.assertEqual(evidence['termination_status'],'not_started')
        for message,reason in [('a password is required','authentication_required'),('unknown option -j','unsupported_tool_option'),('bad configuration option','invalid_configuration'),('cannot talk to daemon','daemon_unavailable')]:
            with patch.dict(probe.os.environ, {'OPSFEAST_SYNTHETIC_DIAGNOSTIC':message+SECRET}):
                _,_,evidence=probe.run([sys.executable,'-c','import sys,os; sys.stderr.write(os.environ["OPSFEAST_SYNTHETIC_DIAGNOSTIC"]); sys.exit(1)'],time.monotonic()+2)
            self.assertEqual(evidence['reason_code'],reason);self.assertNotIn(SECRET,json.dumps(evidence))

    def test_service_ssh_validation_and_descriptor_schema_match(self):
        recipe=SimpleNamespace(vars={'ssh_context':{'user':'incomplete'}},timeout=10,session=Mock())
        with self.assertRaises(ConfigError): service.collect(recipe,'ssh-policy')
        recipe.session.exec_command.assert_not_called()
        for kind, reference in REFERENCES.items():
            metadata=read_yaml(ROOT/'recipes'/reference/'recipe.yaml')
            self.assertEqual(metadata['retention']['data_schema'],schema(kind))


class PolicyDeliveryTests(unittest.TestCase):
    setUp=fixtures.VaultTests.setUp
    enable=fixtures.VaultTests.enable

    def test_all_recipes_run_retain_consume_and_project_without_target_connections(self):
        import recipe_runner, retention_store
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        target=Path(directory.name);files(target)
        class PolicyActor(Actor):
            def exec_command(actor,argv,**options):
                if argv[:3]==['python3','-B','-']:
                    assert options['input']==Path(probe.__file__).read_text()
                    data=snapshot(target,argv[3],options=json.loads(argv[6]),limit=int(argv[4]))
                    return Result(json.dumps(data),'',0)
                return super().exec_command(argv,**options)
        self.enable()
        for kind,reference in REFERENCES.items():
            report,path=recipe_runner.run(self.root,'node',recipe=reference,session_class=PolicyActor,runtime={'verification':'synthetic-only'})
            self.assertIn(report['status'],('success','partial'),report)
            self.assertEqual(report['retention']['status'],'stored',report)
            self.assertNotIn(SECRET,path.read_text())
        self.assertEqual(retention_store.refresh_content(self.root)['status'],'success')
        profile=Instance.open().profile(root=self.root)
        with patch('opsfeast.linux_profile.collect',side_effect=AssertionError('read cannot collect')):
            data=inspect_host(profile,'node',limit=250)
        self.assertEqual(data['retained_record_count'],5)
        ssh=next(p for p in data['items'] if p['property_id']=='policy.ssh_policy')
        self.assertEqual(ssh['state'],'complete')
        self.assertEqual(ssh['evidence'][0]['samples'][0]['basis'],'configured')
        self.assertTrue(ssh['evidence'][0]['commands'])
        self.assertNotIn(SECRET,json.dumps(data))
