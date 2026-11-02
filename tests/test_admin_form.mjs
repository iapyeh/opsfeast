import test from 'node:test';
import assert from 'node:assert/strict';
import {adminInputError,mountAdminSettings} from '../web/assets/admin-settings.mjs';
import {getMessages} from '../web/assets/i18n.mjs';

test('account form explains invalid usernames and counts Unicode code points',()=>{
  assert.equal(adminInputError('使用者','測試密碼'.repeat(4),'測試密碼'.repeat(4)),'usernameHint');
  assert.equal(adminInputError('synthetic','🦉'.repeat(11),'🦉'.repeat(11)),'passwordHint');
  assert.equal(adminInputError('synthetic','🦉'.repeat(256),'🦉'.repeat(256)),null);
  assert.equal(adminInputError('synthetic','🦉'.repeat(257),'🦉'.repeat(257)),'passwordHint');
  assert.equal(adminInputError('synthetic','測試密碼'.repeat(4),'different'),'mismatch');
});

test('account form reports success only for confirmed saved revision',async t=>{
  const priorWindow=globalThis.window,priorDocument=globalThis.document;
  globalThis.window={addEventListener(){}};
  globalThis.document={createElement:()=>({})};
  t.after(()=>{globalThis.window=priorWindow;globalThis.document=priorDocument;});
  for(const confirmed of [true,false]) {
    const nodes=new Map(),links=[];
    const node=selector=>{
      if(!nodes.has(selector))nodes.set(selector,{value:'',textContent:'',events:{},addEventListener(name,fn){this.events[name]=fn;},setAttribute(){},focus(){}});
      return nodes.get(selector);
    };
    const container={innerHTML:'',querySelector:node,append:link=>links.push(link)};
    let calls=0;
    const request=async()=>++calls===1?{configured:false,revision:0,username:null}:{configured:confirmed,revision:confirmed?1:0};
    const m=getMessages('zh-TW');
    await mountAdminSettings(container,{m,e:String,request});
    node('#admin-username').value='synthetic';
    node('#admin-password').value=node('#admin-confirm').value='Synthetic-password-001';
    await node('#admin-save').events.click();
    assert.equal(node('#admin-status').textContent,confirmed?m.admin.saved:m.admin.failed);
    assert.equal(links.length,confirmed?1:0);
    if(confirmed){
      assert.equal(node('.subtle-tag').textContent,m.admin.configured);
      assert.equal(node('#admin-password').value,'');
    }else assert.equal(node('#admin-save').disabled,false);
  }
});
