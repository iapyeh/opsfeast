import copy from './locales/host-draft-zh-TW.mjs';
// Browser-only synthetic models. No host/service API or persistence.
export function pinLogin(users) {
  return [...users.filter(user=>user.login),...users.filter(user=>!user.login)];
}
export function moveUser(users,id,direction) {
  const ordered=pinLogin(users),index=ordered.findIndex(user=>user.id===id),target=index+direction;
  if(index<0||ordered[index].login||target<1||target>=ordered.length)return ordered;
  [ordered[index],ordered[target]]=[ordered[target],ordered[index]];return ordered;
}
export function chooseLogin(users,id) {
  if(!users.some(user=>user.id===id))return users;
  return pinLogin(users.map(user=>({...user,login:user.id===id})));
}
export function seedHost(row) {
  return {connection:{endpoint:row[0]+'.example.invalid',port:'22',group:row[2],enabled:row[4]},users:[{id:'login',name:row[1],login:true,sudo:true},{id:'root',name:'root',login:false,sudo:false},{id:'audit',name:'auditor',login:false,sudo:false}],recipes:[{id:'my-backup-check',enabled:true,values:{days:'7',directory:'/example/backups'}}]};
}
export const recipeCatalog=[
  {id:'my-backup-check',fields:[['days','number','7'],['directory','text','/example/backups']]},
  {id:'my-service-report',fields:[['format','text','markdown']]},
  {id:'system/inventory/overview',fields:[['include_network','checkbox',true]]},
  {id:'feast/report/retention-summary',fields:[['limit','number','20']]}
];
export function hostRecords(host) {
  return copy.historyFixtures.map(record=>({...record,host,lines:[...record.lines]})).sort((a,b)=>b.time.localeCompare(a.time));
}
export function hostLogUrl(record) {
  return '/logs?'+new URLSearchParams({host:record.host,entry:record.id});
}
