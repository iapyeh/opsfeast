"""Small JSON CLI for the interactive HTTP contract; never executes SSH locally."""
import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlparse
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import uuid


def main():
    parser=argparse.ArgumentParser(description='Read/propose interactive work through the local OpsFeast server. Agent credentials cannot approve execution.')
    parser.add_argument('--url',default='http://127.0.0.1:8740')
    parser.add_argument('--token-file',type=Path,required=True)
    parser.add_argument('operation',choices=['list','show','events','create','plan','approve','continue','reject','stop','close','feedback','analysis'])
    parser.add_argument('--work',help='Existing work UUID (required except list/create).')
    parser.add_argument('--after',type=int,default=0,help='Event cursor for events; streams until interrupted.')
    parser.add_argument('--request-id',help='Reuse this ID only for the exact same action body.')
    args=parser.parse_args()
    parsed=urlparse(args.url)
    if parsed.scheme!='http' or parsed.hostname not in ('127.0.0.1','localhost','::1') or parsed.path not in ('','/') or parsed.username or parsed.query or parsed.fragment:
        parser.error('--url must be a loopback HTTP server origin')
    if args.operation not in ('list','create') and not args.work:parser.error('--work is required')
    if args.work:
        try:uuid.UUID(args.work)
        except ValueError:parser.error('--work must be a UUID')
    base=args.url.rstrip('/')+'/api/v1/interactive'
    path='' if args.operation in ('list','create') else '/'+args.work
    body=None
    if args.operation=='events':path+='/events?after='+str(args.after)
    elif args.operation not in ('list','show'):
        raw=sys.stdin.read(65537)
        if len(raw)>65536:parser.error('stdin JSON exceeds 64 KiB')
        try:body=json.loads(raw or '{}')
        except ValueError:parser.error('stdin must be a JSON object')
        if not isinstance(body,dict):parser.error('stdin must be a JSON object')
        if args.operation!='create':
            path+='/'+args.operation
            body['request_id']=args.request_id or body.get('request_id') or str(uuid.uuid4())
    try:
        token=args.token_file.read_text().strip()
        request=Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        with urlopen(request,timeout=65) as response:
            if args.operation=='events':
                for line in response:
                    value=line.decode().strip()
                    if value.startswith('data: '):print(value[6:],flush=True)
            else:print(response.read().decode())
        return 0
    except HTTPError as exc:
        print(exc.read().decode(),file=sys.stderr);return 1
    except (OSError,ValueError) as exc:
        print(type(exc).__name__,file=sys.stderr);return 1

if __name__=='__main__':sys.exit(main())
