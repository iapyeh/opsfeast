"""Host-result history and focused diagnosis under the observation namespace."""
import argparse
import json
from pathlib import Path
import sys

from opsfeast import ConfigError, resolve_root
from console_output import human_output, table, vertical, prepare, display_icons, host_label, ConsoleDependencyError
from display_time import format_time, human_times
from recipe_reports import results, show_result, result_path, page, export_html
from result_diagnostics import diagnose, format_diagnosis


def main(argv=None):
    parser=argparse.ArgumentParser(prog='opsfeast.py observation result',allow_abbrev=False,
        description='Read host results only. No ID lists history; an ID shows focused diagnosis. No connections or writes except an explicit --html export.',
        epilog='Examples: observation result --host node; observation result RESULT_ID; observation result RESULT_ID --detail; observation result RESULT_ID --raw')
    parser.add_argument('result_id',nargs='?',help='short ID or observations/ storage-relative path')
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--detail',action='store_true',help='full vertical detail; without an ID, a vertical index')
    mode.add_argument('--raw',action='store_true',help='emit the original complete JSON; requires RESULT_ID')
    parser.add_argument('--json',action='store_true',help='structured index/diagnosis, or complete raw data with --detail')
    parser.add_argument('--host')
    parser.add_argument('--recipe-id')
    parser.add_argument('--status',choices=('success','partial','failed','skipped','unsupported'))
    parser.add_argument('--limit',type=int,help='diagnosis only: maximum problems, 1–50 (default 5)')
    parser.add_argument('--html',type=Path,help='write a new HTML index, or full selected detail with --detail')
    environment=parser.add_mutually_exclusive_group()
    environment.add_argument('--root',type=Path)
    environment.add_argument('--profile')
    args=parser.parse_args(argv)
    try:
        if args.raw and args.result_id is None:
            raise ConfigError('--raw requires RESULT_ID')
        if args.result_id is not None and (args.host or args.recipe_id or args.status):
            raise ConfigError('RESULT_ID cannot be combined with index filters')
        if args.limit is not None and (args.result_id is None or args.detail or args.raw or args.html):
            raise ConfigError('--limit applies only to focused diagnosis of RESULT_ID')
        if args.html and (args.raw or (args.result_id is not None and not args.detail)):
            raise ConfigError('--html supports the index or RESULT_ID --detail')
        if not args.raw and not args.detail and not args.html and args.result_id is None:
            prepare(args.json)
        root=resolve_root(args.root,args.profile).resolve(strict=True)
        if args.result_id is not None:
            if args.detail or args.raw:
                data=show_result(root,args.result_id,kind='operation')
                if args.html:
                    rows=[[key,json.dumps(human_times(value),ensure_ascii=False)] for key,value in data.items()]
                    receipt={'html_path':export_html(args.html,page('OpsFeast host result',['Field','Value'],rows,'Saved evidence; timestamps displayed in controller local time.'))}
                    print(json.dumps(receipt,indent=2))
                elif args.raw or args.json:
                    print(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False))
                else:
                    identifier=result_path(root,args.result_id).relative_to(root).as_posix()
                    print(vertical({'result_id':identifier,**data}))
            else:
                data=diagnose(root,args.result_id,limit=args.limit if args.limit is not None else 5,kind='operation')
                print(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False) if args.json else format_diagnosis(data))
            return 0
        data=results(root,args.recipe_id,args.host,args.status,kind='operation')
        rows=[[r['short_id'],r['recipe_id'],r['host_id'],r['status'],format_time(r['completed_at']),r.get('collection_user') or 'unknown',json.dumps(r['identity_warnings'],ensure_ascii=False)] for r in data['results']]
        if args.html:
            receipt={'html_path':export_html(args.html,page('OpsFeast host results',['Result ID','Recipe','Host','Status','Completed','User','Identity warnings'],rows,json.dumps(data['errors'],ensure_ascii=False))),'status':data['status']}
            print(json.dumps(receipt,indent=2))
        elif args.json:
            print(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False))
        elif args.detail:
            for index,item in enumerate(data['results'],1):
                print('******** Result '+str(index)+' ********')
                print(vertical(item))
                print()
            if not data['results']:print('No saved results.')
        elif human_output():
            icons=display_icons(root)
            for row in rows:row[2]=host_label(row[2],icons) if row[2] else '-'
            print(table(['result ID','recipe','host','status','completed','user'],[row[:-1] for row in rows]))
        else:
            for row in rows:print(' | '.join(str(value) for value in row))
        if not args.json and not args.html:
            for error in data['errors']:
                print('ERROR: '+error.get('short_id',error['result_id'])+' invalid result')
        return 0 if data['status']=='success' else 1
    except (ConfigError,OSError,ValueError,ImportError,ConsoleDependencyError) as exc:
        print('ERROR: '+str(exc),file=sys.stderr)
        return 1
