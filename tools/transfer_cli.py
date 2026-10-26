"""Local package transfer, reviewed import and recoverable archive commands."""
import argparse
import json
from pathlib import Path
import sqlite3
from opsfeast import ConfigError, resolve_root
from opsfeast import transfer


def main(argv=None):
    parser=argparse.ArgumentParser(prog='opsfeast.py transfer',allow_abbrev=False,
        description='Copy or archive observations/retention independently; inspect/import packages and install reviewed recipes. No connections, recipe execution, consumer activation or external delivery.')
    parser.add_argument('action',choices=('list','show','export','import-plan','import','archive-plan','archive','resume','receipts','recipe-plan','recipe-install','recipe-rollback-plan','recipe-rollback','rebuild','import-recovery-plan','import-recover'))
    parser.add_argument('identifier',nargs='?',help='unit ID or archive receipt ID')
    scope=parser.add_mutually_exclusive_group();scope.add_argument('--root',type=Path);scope.add_argument('--profile')
    parser.add_argument('--kind',action='append',choices=transfer.KINDS)
    parser.add_argument('--id',action='append',dest='ids',help='select exact portable unit IDs')
    parser.add_argument('--recipe',help='exact recipe reference')
    parser.add_argument('--host',action='append')
    parser.add_argument('--older-than',type=int,help='strictly older than this many days')
    parser.add_argument('--before',help='exclusive timezone-aware cutoff')
    parser.add_argument('--package',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--mode',choices=('merge','replace'),default='merge')
    parser.add_argument('--plan',help='reviewed current plan sha256; required for mutations')
    parser.add_argument('--path',help='recipe installation path relative to profile recipes/')
    parser.add_argument('--resolution',choices=('conflict','replace','skip'),default='conflict')
    parser.add_argument('--json',action='store_true')
    args=parser.parse_args(argv)
    def require(*names):
        if any(getattr(args,n) is None for n in names):parser.error('action requires '+', '.join('--'+n for n in names))
    if args.action=='archive' and any(v is not None for v in (args.kind,args.recipe,args.host,args.ids,args.older_than,args.before)):
        parser.error('archive uses the frozen plan; selection flags belong to archive-plan')
    if args.action in ('import','archive','recipe-install','recipe-rollback','import-recover'):
        require('plan')
    try:
        root=resolve_root(args.root,args.profile).resolve(strict=True)
        selection=dict(kinds=args.kind or transfer.KINDS,recipe=args.recipe,hosts=args.host,ids=args.ids,older_than=args.older_than,before=args.before)
        if args.action in ('list','show'):
            units=transfer.query(root,recipe=args.recipe,hosts=args.host)
            if args.kind:units=[u for u in units if u['kind'] in args.kind]
            if args.action=='show':
                selected=[u for u in units if u['id']==args.identifier]
                if len(selected)!=1:raise ConfigError('portable unit not found')
                result=selected[0]
            else:result=transfer.select(root,**selection)
        elif args.action=='export':
            require('output');result=transfer.export(root,args.output,**selection)
        elif args.action in ('import-plan','import'):
            require('package')
            result=transfer.import_plan(root,args.package,args.mode) if args.action=='import-plan' else transfer.import_package(root,args.package,mode=args.mode,expected_plan=args.plan)
        elif args.action in ('archive-plan','archive'):
            require('output')
            result=transfer.archive_plan(root,args.output,**selection) if args.action=='archive-plan' else transfer.archive(root,args.output,expected_plan=args.plan,**selection)
        elif args.action=='resume':
            if not args.identifier:parser.error('resume requires archive receipt ID')
            result=transfer.archive(root,resume=args.identifier)
        elif args.action in ('import-recovery-plan','import-recover'):
            if not args.identifier:parser.error('import recovery requires receipt ID')
            result=transfer.import_recovery_plan(root,args.identifier) if args.action=='import-recovery-plan' else transfer.recover_import(root,args.identifier,expected_plan=args.plan)
        elif args.action=='rebuild':result=transfer.publish(root)
        elif args.action in ('recipe-rollback-plan','recipe-rollback'):
            if not args.identifier:parser.error('recipe rollback requires receipt ID')
            from opsfeast.recipe_install import rollback_plan,rollback
            result=rollback_plan(root,args.identifier) if args.action=='recipe-rollback-plan' else rollback(root,args.identifier,expected_plan=args.plan)
        elif args.action=='receipts':result={'receipts':transfer.receipts(root)}
        else:
            require('package','path')
            from opsfeast.recipe_install import plan,install
            result=plan(root,args.package,args.path,resolution=args.resolution) if args.action=='recipe-plan' else install(root,args.package,args.path,resolution=args.resolution,expected_plan=args.plan)
        print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False));return 0
    except (ConfigError,OSError,ValueError,TypeError,sqlite3.Error) as exc:
        print(json.dumps({'status':'failed','error_type':type(exc).__name__,'message':str(exc)},ensure_ascii=False));return 1
