import test from 'node:test';
import assert from 'node:assert/strict';
import {hostManagementUrl,filterManagedHosts,normalizeHostGroups} from '../web/assets/host-manager.mjs';
test('host links retain explicit profile and encode opaque host IDs',()=>{
  const url=new URL(hostManagementUrl('prod','a/b & c','settings'),'http://localhost');
  assert.equal(url.searchParams.get('profile'),'prod');assert.equal(url.searchParams.get('host'),'a/b & c');
  assert.equal(url.searchParams.get('view'),'settings');
});
test('real-host filters preserve empty inventory addresses and multiple groups',()=>{
  const hosts=[{host_id:'Web-01',groups:['prod','linux'],reference_ips:{ipv4_addresses:[]}}, {host_id:'DB-01',groups:['prod']}];
  assert.deepEqual(filterManagedHosts(hosts,' WEB ','linux'),[hosts[0]]);
  assert.deepEqual(filterManagedHosts(hosts,'DB','linux'),[]);
  assert.deepEqual(hosts[0].reference_ips.ipv4_addresses,[]);
  assert.deepEqual(normalizeHostGroups(['prod',' linux ','prod','']),['prod','linux']);
});
