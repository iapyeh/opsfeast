import test from 'node:test';
import assert from 'node:assert/strict';
import {consume,displayText,preview,blockDisplayText,readBlockText,visibleInRiver,identityLabel,processingState,activityState} from '../web/assets/console-reader-state.mjs';
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

test('empty output streams and a runner outcome have distinct reader labels',()=>{
  for(const kind of ['stdout','stderr']){
    assert.equal(blockDisplayText({kind,status:'completed',size:0},''),kind+'：沒有輸出。');
    assert.equal(blockDisplayText({kind,status:'streaming',size:0},''),'');
    assert.equal(blockDisplayText({kind,status:'completed',size:3},'ok\n'),'ok\n');
  }
  const head='{"status": "partial", "output": {"exit_code": 1}}';
  assert.equal(blockDisplayText({kind:'status',title:'dispatch',head},head),'Recipe runner：部分完成（runner 退出碼 1）');
  assert.equal(blockDisplayText({kind:'stdout',title:'dispatch',head},head),head);
});

test('copy reads original text in byte-offset pages without including subsequent output',async()=>{
  const original='臺銀\nsecond';
  const size=new TextEncoder().encode(original).length;
  const calls=[];
  const text=await readBlockText({head:'臺銀',tail:'second',size},async(offset,limit)=>{
    calls.push([offset,limit]);
    return offset===0?{text:'臺銀\n',next_offset:7}:{text:'second\nlate',next_offset:size+5};
  });
  assert.equal(text,original);
  assert.deepEqual(calls,[[0,256],[7,256]]);
  assert.equal(await readBlockText({head:original,size},()=>assert.fail('complete head should not fetch')),original);
  await assert.rejects(readBlockText({head:'',size},async()=>({text:'',next_offset:0})),/incomplete_block_content/);
});

test('identity metadata stays outside river content and has a readable toolbar label',()=>{
  const block={kind:'identity',head:JSON.stringify({host:'synthetic',connection_user:'test',effective_user:'root',identity_verified:true})};
  assert.equal(visibleInRiver(block),false);
  assert.equal(visibleInRiver({kind:'stdout'}),true);
  assert.equal(visibleInRiver({kind:'status'}),true);
  assert.equal(identityLabel(block),'synthetic · 登入 test · 目前 root · 身分已核對');
  assert.doesNotMatch(identityLabel({...block,head:'legacy private text'}),/legacy/);
});
test('processing follows unfinished work through completion, failure and restored snapshots',()=>{
  for(const kind of ['command','analysis','status']){
    const b={kind,status:'streaming'};
    assert.equal(processingState([b]).busy,true);
    for(const status of ['completed','failed','interrupted','cancelled'])
      assert.equal(processingState([{...b,status}]).busy,false);
  }
  assert.equal(processingState([]).busy,false);
  assert.equal(processingState([{kind:'stdout',status:'streaming'}]).busy,false);
  const initial={session:{session_id:'one'},seq:0,blocks:[]};
  const first=consume(initial,{session_id:'one',seq:1,block:{id:'command',kind:'command',status:'streaming'}});
  assert.equal(processingState(first.blocks).busy,true);
  const done=consume(first,{session_id:'one',seq:2,block:{id:'command',kind:'command',status:'failed'}});
  assert.equal(processingState(done.blocks).busy,false);
});
test('thinking fills the command handoff, expires locally and clears on next input or chat report',()=>{
 const now=Date.parse('2026-01-01T00:00:00Z');
 const initial={session:{session_id:'one'},seq:0,blocks:[{id:'command',kind:'command',status:'completed'}]};
 const activity={state:'thinking',updated_at:new Date(now).toISOString(),expires_at:new Date(now+120000).toISOString()};
 const thinking=consume(initial,{type:'activity.updated',session_id:'one',seq:1,activity});
 assert.equal(thinking.blocks,initial.blocks);
 assert.deepEqual(activityState(thinking,now),{busy:false,thinking:true,label:'Agent 思考中…'});
 assert.equal(activityState(thinking,now+120000).thinking,false);
 assert.equal(activityState(thinking,now+120000).label,'Agent 狀態未更新');
 const running={...thinking,blocks:[{id:'next',kind:'command',status:'streaming'}]};
 assert.equal(activityState(running,now).busy,true);assert.equal(activityState(running,now).thinking,false);
 const idle={state:'idle',expires_at:null};
 const chat=consume(thinking,{type:'activity.updated',session_id:'one',seq:2,activity:idle});
 assert.equal(activityState(chat,now).thinking,false);
 const command=consume(thinking,{type:'block.created',session_id:'one',seq:2,activity:idle,block:{id:'next',kind:'command',status:'streaming'}});
 assert.equal(command.session.activity.state,'idle');assert.equal(activityState(command,now).busy,true);
 assert.equal(consume(command,{type:'activity.updated',session_id:'one',seq:1,activity}),command);
 assert.throws(()=>consume(thinking,{type:'activity.updated',session_id:'one',seq:3,activity}),/event_gap/);
 assert.equal(activityState({...thinking,session:{activity:{state:'thinking',expires_at:'bad'}}},now).thinking,false);
});
