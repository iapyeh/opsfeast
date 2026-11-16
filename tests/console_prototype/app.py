"""Loopback-only browser TEST UI. Not wired into OpsFeast Home or its Core API."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
from adapter import Bridge

HTML = r'''<!doctype html><html><head><meta charset="utf-8"><title>OpsFeast Console Validation</title>
<style>body{font:16px system-ui;background:#101927;color:#e2e8f0;margin:28px;max-width:1250px}h1{font-size:26px}button,input,select{font:inherit;padding:9px;margin:4px;border-radius:6px}button{cursor:pointer}input{width:65%}pre{white-space:pre-wrap;background:#19263a;padding:14px;border-radius:8px;max-height:320px;overflow:auto}.warning{color:#ffcf72}.state{font-size:23px;font-weight:700}table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:6px;border-bottom:1px solid #40516b}.bar{display:flex;gap:15px}#events{font-size:13px}#counter{color:#9dd5ff}</style></head>
<body><h1>OpsFeast · Embedded Console Validation</h1><p class="warning">TEST ADAPTER — synthetic settings only; local Bash/PTY or simulated identities. No SSH / native su / sudo. Not a production integration.</p>
<div><select id="mode" aria-label="Fixture mode"><option value="local">Real local PTY</option><option value="simulated">Simulated accounts / jump metadata</option></select>
<select id="fault" aria-label="Fault injection"><option value="">No fault</option><option>initialization</option><option>cleanup</option><option>restoration</option><option>disconnect</option><option>channel_disconnect</option></select>
<button onclick="act('open',mode.value,{fault:fault.value||null})">Open fixture</button><button onclick="act('close')">Close console</button><button onclick="act('reuse')">Probe owner reuse</button></div>
<div class="bar"><p>State: <span id="state" class="state">closed</span></p><p>Session reuse: <strong id="reuse">unknown</strong></p><p id="counter"></p></div>
<p id="details"></p><table><thead><tr><th>Layer</th><th>Connection</th><th>SSH/SFTP login</th><th>Shell effective identity</th><th>Evidence</th></tr></thead><tbody id="layers"></tbody></table>
<p class="warning">Identity verification is an entry observation. Program layers and uncertain recovery are unverified. Host has no TTY; shell defaults to PTY. Arbitrary Python evaluation is synchronous and cannot be safely preempted. Shell jobs reject stdin; use Enter Python for interaction.</p>
<input id="source" aria-label="Console input" placeholder="Python or dollar input (not stored in history)"><button onclick="act('submit',source.value)">Submit cell</button><button onclick="act('start',source.value,{timeout:Number(budget.value)})">Start shell job</button><label>seconds <input style="width:70px" id="budget" aria-label="Job timeout" value="5"></label>
<div><button onclick="act('enter')">Enter Python</button><button onclick="act('input',source.value)">Send program input</button><button onclick="act('shell')">Nested shell</button><button onclick="act('interrupt')">Ctrl-C</button><button onclick="act('eof')">EOF</button><button onclick="act('leave')">Leave one layer</button><button onclick="act('host_exception')">Host exception</button></div>
<div><input id="account" aria-label="Target account" placeholder="Declared synthetic target" style="width:260px"><button onclick="act('su',account.value)">Simulated su</button><button onclick="act('sudo',account.value)">Simulated sudo</button></div>
<h2>Output</h2><pre id="output"></pre><h2>Structured event evidence</h2><pre id="events"></pre>
<script>const token='TOKEN';let last=0,ticks=0;const el=id=>document.getElementById(id);async function act(op,value='',options={}){await fetch('/action',{method:'POST',headers:{'Content-Type':'application/json','X-Test-Token':token},body:JSON.stringify({op,value,...options})});}window.act=act;
async function refresh(){try{const data=await(await fetch('/state')).json(),c=data.current;el('state').textContent=c.state;el('reuse').textContent=c.session_reuse;el('details').textContent=`evidence=${c.evidence||'none'} | exitcode=${c.exitcode??'unknown'} | error=${c.error_type||'none'} | stop=${c.stop_reason||'none'} | termination=${c.termination_status||'unknown'} | same Session=${c.same_session??'n/a'} | owner closed=${c.owner_closed??'n/a'} | ancestor closed=${c.ancestor_closed??'n/a'} | worker=${c.worker_thread||'n/a'}`;
el('layers').replaceChildren();for(const env of c.environments||[]){const row=document.createElement('tr');for(const value of [env.kind,env.host,env.connection_user??'not SSH (local)',env.identity_verified?env.effective_user:`${env.effective_user} (unverified)`,env.identity_verified?'verified on entry':'unknown / inherited']){const cell=document.createElement('td');cell.textContent=value;row.append(cell);}el('layers').append(row);}for(const event of data.events){if(event.sequence>last){el('output').textContent+=event.stdout+event.stderr;last=event.sequence;}}el('events').textContent=data.events.slice(-7).map(e=>JSON.stringify(e)).join('\n');el('counter').textContent=`UI heartbeat ${++ticks} · event ${last}`;}catch(e){}setTimeout(refresh,120);}refresh();</script></body></html>'''


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--journal', required=True)
    args=parser.parse_args()
    bridge=Bridge(args.journal)
    token=secrets.token_urlsafe(24)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_GET(self):
            body=(json.dumps(bridge.snapshot()).encode() if self.path=='/state' else HTML.replace('TOKEN',token).encode())
            self.send_response(200);self.send_header('Content-Type','application/json' if self.path=='/state' else 'text/html; charset=utf-8');self.end_headers();self.wfile.write(body)
        def do_POST(self):
            if self.headers.get('X-Test-Token')!=token:
                self.send_error(403);return
            data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            op,value=data.pop('op'),data.pop('value','')
            if op not in {'open','close','reuse','submit','start','enter','input','shell','interrupt','eof','leave','su','sudo','host_exception'}:
                self.send_error(400);return
            bridge.request(op,value,**data)
            self.send_response(202);self.end_headers();self.wfile.write(b'queued')
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'TEST UI http://127.0.0.1:{args.port}',flush=True)
    try: server.serve_forever()
    finally: bridge.stop();server.server_close()

if __name__=='__main__': main()
