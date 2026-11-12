import {spawn} from 'node:child_process';
import {readFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
// Run against the separate synthetic fixture, never a human installation.
const [chrome,metadata]=process.argv.slice(2);
if(!chrome||!metadata)throw new Error('Usage: node note_bundle_smoke.mjs /path/to/chrome /path/to/synthetic-fixture.json');
const fixture=JSON.parse(readFileSync(metadata,'utf8'));
if(!/^http:\/\/127\.0\.0\.1:[0-9]+$/.test(fixture.origin))throw new Error('A local synthetic fixture is required');
const userData=mkdtempSync(join(tmpdir(),'opsfeast-browser-'));
const processChrome=spawn(chrome,['--headless=new','--remote-debugging-port=0','--user-data-dir='+userData,'--no-first-run','--no-default-browser-check','--disable-background-networking','--disable-component-update','--disable-sync','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--host-resolver-rules=MAP *.invalid ~NOTFOUND','about:blank'],{stdio:['ignore','ignore','pipe']});
let stderr='',socket;
try{
 const endpoint=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(new Error('Chrome debugger not ready: '+stderr.slice(-500))),15000);processChrome.stderr.on('data',chunk=>{stderr+=chunk;const match=stderr.match(/DevTools listening on (ws:\/\/[^\s]+)/);if(match){clearTimeout(timer);resolve(match[1]);}});processChrome.on('exit',code=>reject(new Error('Chrome exited '+code)));});
 socket=new WebSocket(endpoint);await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
 let next=0;const pending=new Map(),events=[];
 socket.onmessage=event=>{const item=JSON.parse(event.data);if(item.id){const entry=pending.get(item.id);pending.delete(item.id);if(item.error)entry.reject(new Error(JSON.stringify(item.error)));else entry.resolve(item.result);}else events.push(item);};
 const send=(method,params={},sessionId)=>new Promise((resolve,reject)=>{const id=++next;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params,...(sessionId?{sessionId}:{})}));});
 const {targetId}=await send('Target.createTarget',{url:'about:blank'});const {sessionId}=await send('Target.attachToTarget',{targetId,flatten:true});
 await send('Page.enable',{},sessionId);await send('Runtime.enable',{},sessionId);await send('Log.enable',{},sessionId);await send('Network.enable',{},sessionId);
 async function evaluate(expression){const result=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true},sessionId);if(result.exceptionDetails)throw new Error(result.exceptionDetails.text+': '+result.exceptionDetails.exception?.description);return result.result.value;}
 async function wait(expression){for(let i=0;i<100;i++){try{const value=await evaluate(expression);if(value)return value;}catch{}await new Promise(resolve=>setTimeout(resolve,100));}throw new Error('Timed out: '+expression+'; logs '+JSON.stringify(events.filter(e=>e.method==='Log.entryAdded').slice(-5)));}
 const navigate=async path=>{const url=path.startsWith('http')?path:fixture.origin+path;const result=await send('Page.navigate',{url},sessionId);if(result.errorText)throw new Error('Navigation failed: '+result.errorText);await wait('location.href === '+JSON.stringify(url)+' && document.readyState === "complete"');};
 await navigate('/login');
 const status=await evaluate(`fetch('/api/v1/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:'test-owner',password:'synthetic-browser-test'})}).then(r=>r.status)`);if(status!==200)throw new Error('Synthetic login failed '+status);
 await navigate('/hosts?profile=main&host=sample&view=notes');await wait('document.querySelector("[data-note-attach]")');
 await evaluate('document.querySelector("[data-note-attach]").click()');
 const {root}=await send('DOM.getDocument',{},sessionId);const {nodeId}=await send('DOM.querySelector',{nodeId:root.nodeId,selector:'#bundle-form input[name=archive]'},sessionId);
 await send('DOM.setFileInputFiles',{nodeId,files:[fixture.upload_zip]},sessionId);
 await evaluate('document.querySelector("#bundle-form").requestSubmit()');
 await wait('document.querySelectorAll(".note-attachment > a[target]").length === 2');
 const mdLink=await evaluate('document.querySelectorAll(".note-attachment > a[target]")[1].href');
 await navigate(mdLink);await wait('document.querySelector(".note-document img")?.naturalWidth === 16');
 const markdown=await evaluate('({table:!!document.querySelector(".note-document table"),image:document.querySelector(".note-document img").naturalWidth,escaped:document.querySelector(".note-document").textContent.includes("<script>"),rawHtmlDidNotRun:window.markdownUnsafe===undefined,code:document.querySelector(".note-document pre").textContent})');
 if(!markdown.table||!markdown.escaped||!markdown.rawHtmlDidNotRun)throw new Error('Bad Markdown result '+JSON.stringify(markdown));
 await navigate('/note-attachments?'+new URLSearchParams(fixture.html_scope));await wait('document.querySelector("#bundle-open-preview")');
 await evaluate('window.bundleMessages=[];window.addEventListener("message",event=>window.bundleMessages.push(event.data));document.querySelector("#bundle-open-preview").click()');
 const interactive=await wait('window.bundleMessages?.find(message=>message?.bundleReady)');
 if(!interactive.parentBlocked||!interactive.cookieBlocked||!interactive.networkBlocked||!interactive.webgl||interactive.three!=='180'||interactive.data!=='package-local-json')throw new Error('Isolation/WebGL result '+JSON.stringify(interactive));
 await evaluate('document.querySelector("iframe").contentWindow.postMessage("test-navigation","*")');
 await new Promise(resolve=>setTimeout(resolve,700));
 const blocked=events.filter(e=>e.method==='Log.entryAdded').map(e=>e.params.entry.text).filter(text=>text.includes('frame-src')&&text.includes('leak=synthetic'));
 if(!blocked.length)throw new Error('Expected CSP navigation block not observed: '+JSON.stringify(events.filter(e=>e.method==='Log.entryAdded').slice(-6)));
 await evaluate('document.querySelector("#bundle-stop-preview").click()');if(await evaluate('!!document.querySelector("iframe")'))throw new Error('Stop did not remove frame');
 const result={markdown,interactive,navigationBlocked:true,stopRemovedFrame:true};console.log(JSON.stringify(result));
 await send('Target.closeTarget',{targetId});
}finally{
 if(socket)socket.close();processChrome.kill('SIGTERM');
 if(processChrome.exitCode===null)await new Promise(resolve=>{const timer=setTimeout(()=>{processChrome.kill('SIGKILL');resolve();},5000);processChrome.once('exit',()=>{clearTimeout(timer);resolve();});});
 rmSync(userData,{recursive:true,force:true});
}
