import test from 'node:test';
import assert from 'node:assert/strict';
import {consume,displayText,preview,visibleInRiver,identityLabel} from '../web/assets/console-reader-state.mjs';
test('stream updates one block without retaining every text chunk in browser history',()=>{
  const original={session:{session_id:'one'},seq:0,blocks:[]};
  const e={session_id:'one',seq:1,block:{id:'b',revision:1,head:'first',tail:'',size:5}};
  const first=consume(original,e),second=consume(first,{...e,seq:2,block:{...e.block,revision:2,head:'first second',size:12}});
  assert.equal(original.blocks.length,0);assert.equal(second.blocks.length,1);
  assert.equal(second.blocks[0].size,12);assert.equal(consume(second,e),second);
  assert.throws(()=>consume(second,{...e,seq:4}),/event_gap/);
  assert.throws(()=>consume(second,{...e,session_id:'other',seq:3}),/wrong_session/);
  assert.match(preview({...e.block,tail:'last'}),/完整內容/);
  assert.equal(preview({...e.block,tail:'last'},true),'first\n⋯\nlast');
});
test('display handles CR progress and ANSI while preserving plain text',()=>{
  assert.equal(displayText('first\r\n10%\r20%\n繁體\x1b[31m文字\x1b[0m'),'first\n20%\n繁體文字');
});

test('identity metadata stays outside river content and has a readable toolbar label',()=>{
  const block={kind:'identity',head:JSON.stringify({host:'synthetic',connection_user:'test',effective_user:'root',identity_verified:true})};
  assert.equal(visibleInRiver(block),false);
  assert.equal(visibleInRiver({kind:'stdout'}),true);
  assert.equal(visibleInRiver({kind:'status'}),true);
  assert.equal(identityLabel(block),'synthetic · 登入 test · 目前 root · 身分已核對');
  assert.doesNotMatch(identityLabel({...block,head:'legacy private text'}),/legacy/);
});
