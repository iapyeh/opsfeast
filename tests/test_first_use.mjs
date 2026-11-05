import test from 'node:test';
import assert from 'node:assert/strict';
import {setupPhase,setupProgress} from '../web/assets/first-use.mjs';
import {getMessages} from '../web/assets/i18n.mjs';
const state={schema_version:'0.1.0',admin_configured:false,authenticated:false,edit_unlocked:false,agent_control_available:true};
test('first-use steps come from server evidence and preserve account authorization',()=>{
  assert.equal(setupPhase(state),'verify');
  assert.equal(setupPhase({...state,edit_unlocked:true}),'verify');
  assert.equal(setupPhase({...state,admin_configured:true,edit_unlocked:true}),'login');
  assert.equal(setupPhase({...state,admin_configured:true}),'login');
  assert.equal(setupPhase({...state,admin_configured:true,authenticated:true}),'appearance');
  assert.equal(setupPhase({...state,agent_control_available:false}),'unavailable');
  assert.equal(setupPhase(null),'unavailable');
  assert.equal(setupPhase({...state,admin_configured:'false'}),'unavailable');
});
test('progress and token instructions are localized and do not embed secret values',()=>{
  const l=getMessages('zh-TW').firstUse;
  const html=setupProgress(l,'account',String);
  assert.equal((html.match(/aria-current="step"/g)||[]).length,1);
  assert.match(html,/建立管理帳號/);
  assert.match(html,/可稍後設定/);
  assert.match(l.agentPrompt,/最高權限/);
  assert.doesNotMatch(l.agentPrompt,/\.token/);
});
