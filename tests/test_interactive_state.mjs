import test from 'node:test';
import assert from 'node:assert/strict';
import {applyDelta,consumeEvent,nextAction,canApprove} from '../web/assets/interactive-state.mjs';
test('stream deltas compose into history without replaying executable effects',()=>{
  let snapshot={protocol_version:'0.1.0',seq:0,state:{work_id:'one',history:[],current:null,status:'draft'}};
  const event=(seq,delta)=>({work_id:'one',seq,delta});
  snapshot=consumeEvent(snapshot,event(1,[{op:'set',path:['current'],value:{stdout:'',command:'do not execute',status:'running'}}]));
  snapshot=consumeEvent(snapshot,event(2,[{op:'append_text',path:['current','stdout'],value:'first\n'}]));
  snapshot=consumeEvent(snapshot,event(3,[{op:'append_text',path:['current','stdout'],value:'second\n'}]));
  snapshot=consumeEvent(snapshot,event(4,[{op:'append',path:['history'],value:snapshot.state.current},{op:'set',path:['current'],value:null},{op:'set',path:['status'],value:'paused'}]));
  assert.equal(snapshot.state.history[0].stdout,'first\nsecond\n');
  assert.equal(snapshot.state.current,null);assert.equal(snapshot.state.status,'paused');
  assert.equal(consumeEvent(snapshot,event(3,[])),snapshot);
  assert.throws(()=>consumeEvent(snapshot,event(6,[])),/event_gap/);
  assert.throws(()=>consumeEvent(snapshot,{work_id:'different',seq:5,delta:[]}),/wrong_work/);
});
test('patches reject prototype paths and preserve previous snapshots',()=>{
  assert.throws(()=>applyDelta({},[{op:'set',path:['__proto__'],value:{polluted:true}}]),/invalid_delta_path/);
  assert.equal({}.polluted,undefined);
  const previous={history:[]};const next=applyDelta(previous,[{op:'append',path:['history'],value:{text:'<script>untrusted</script>'}}]);
  assert.equal(previous.history.length,0);assert.equal(next.history.length,1);
});
test('terminal and recoverable failures give distinct next actions without implying agent wakeup',()=>{
  for(const status of ['failed','interrupted','closed'])assert.match(nextAction({status}),/建立新工作/);
  assert.match(nextAction({status:'failed_step'}),/修正計畫/);
  assert.match(nextAction({status:'paused'}),/確認並執行/);
  assert.equal(nextAction({status:'running'}),'');
});
test('final checkpoint cannot request another approval while an intermediate checkpoint can',()=>{
  const state={status:'paused',plan:{next:3,steps:[{},{},{}]}};
  assert.equal(canApprove(state),false);
  assert.match(nextAction(state),/沒有待執行的下一步/);
  state.plan.next=2;
  assert.equal(canApprove(state),true);
  assert.match(nextAction(state),/確認並執行/);
  state.status='failed_step';
  assert.equal(canApprove(state),false);
});
