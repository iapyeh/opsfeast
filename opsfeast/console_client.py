"""Console blocks JSON client; loopback only, no execution or automatic write retries."""
import argparse
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlparse
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from .console_records import identifier,RecordError

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8740')
    parser.add_argument('--token-file',type=Path,required=True)
    parser.add_argument('operation',choices=['create','block','append','finish','show','content','stream','responses','wait'])
    parser.add_argument('--session');parser.add_argument('--block')
    parser.add_argument('--after',type=int,default=0)
    parser.add_argument('--offset',type=int,default=0)
    parser.add_argument('--limit',type=int,default=16384)
    parser.add_argument('--timeout',type=int,default=30,help='wait for human response, 1–60 seconds; no agent wakeup')
    args=parser.parse_args();url=urlparse(args.url)
    if url.scheme!='http' or url.hostname not in ('127.0.0.1','localhost','::1') or url.path not in ('','/') or url.username or url.query or url.fragment:parser.error('--url must be a loopback HTTP origin')
    if args.operation!='create':
        try:identifier(args.session)
        except RecordError:parser.error('--session must be a UUID')
    if args.operation in ('append','finish','content'):
        try:identifier(args.block)
        except RecordError:parser.error('--block must be a UUID')
    if not 1<=args.timeout<=60:parser.error('--timeout must be 1–60')
    base=args.url.rstrip('/')+'/api/v1/console-sessions'
    path='' if args.operation=='create' else '/'+args.session
    if args.operation=='block':path+='/blocks'
    if args.operation in ('append','finish','content'):path+='/blocks/'+args.block+'/'+args.operation
    if args.operation=='content':path+=f'?offset={args.offset}&limit={args.limit}'
    if args.operation=='stream':path+='/stream?after='+str(args.after)
    if args.operation=='responses':path+='/responses?after='+str(args.after)
    try:
        token=args.token_file.read_text().strip()
        def call(path,body=None,stream=False):
            req=Request(base+path,data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
            with urlopen(req,timeout=65) as response:
                if stream:
                    for line in response:
                        if line.startswith(b'data: '):print(line[6:].decode().strip(),flush=True)
                else:return json.load(response)
        if args.operation=='wait':
            deadline=time.monotonic()+args.timeout;cursor=args.after
            while time.monotonic()<deadline:
                remaining=max(0,min(25,int(deadline-time.monotonic())))
                data=call('/'+args.session+f'/responses?after={cursor}&wait={remaining}');cursor=data['seq']
                if data['responses']:print(json.dumps(data,ensure_ascii=False));return 0
                if remaining==0:break
            print(json.dumps({'seq':cursor,'responses':[],'timed_out':True}));return 0
        body=None
        if args.operation in ('create','block','append','finish'):
            raw=sys.stdin.read(65537)
            if len(raw.encode())>65536:parser.error('JSON exceeds 64 KiB')
            body=json.loads(raw)
            if not isinstance(body,dict):parser.error('JSON object required')
        result=call(path,body,args.operation=='stream')
        if args.operation!='stream':print(json.dumps(result,ensure_ascii=False))
        return 0
    except HTTPError as exc:print(exc.read().decode(),file=sys.stderr);return 1
    except (OSError,ValueError) as exc:print(type(exc).__name__,file=sys.stderr);return 1
    except KeyboardInterrupt:return 130

if __name__=='__main__':sys.exit(main())
