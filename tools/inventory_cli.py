"""Human/agent interface for selective inventory, schedules and the cron dispatcher."""
import argparse
import json
from pathlib import Path
import sys

from opsfeast import ConfigError, resolve_root, positive_timeout
import inventory_jobs as service
import inventory_schedule as schedule
from retention_store import checked, atomic, canonical
from console_output import prepare as prepare_console, ConsoleDependencyError


def main(argv=None):
    parser = argparse.ArgumentParser(prog='opsfeast.py inventory',allow_abbrev=False,
        description='Inspect inventory properties, query hosts without storage, save explicit refreshes, and manage opt-in periodic collection.')
    commands = parser.add_subparsers(dest='command',required=True)
    desc = commands.add_parser('describe',description='Read the bundled job/property catalog and fixed YANG module revisions. No profile, connection or writes.',
                               help='discover jobs, properties and YANG mappings')
    desc.add_argument('--job',action='append',default=[])
    for action,description in [('query','Acquire selected properties immediately. No OpsFeast writes unless --save. No scheduler state changes.'),
                               ('run','Acquire selected jobs immediately and save raw/retained observations plus configured consumer updates. No scheduler state changes.')]:
        sub = commands.add_parser(action,description=description,help=description,
             epilog=('Example: opsfeast.py inventory '+('query --host node --property storage.filesystems.used_percent --save --note "After log cleanup"' if action=='query' else 'run --host node --job storage-capacity')))
        sub.add_argument('--host',required=True)
        sub.add_argument('--recipe',default='system/inventory/overview')
        sub.add_argument('--property',action='append',default=[])
        sub.add_argument('--job',action='append',default=[])
        sub.add_argument('--note',default='')
        sub.add_argument('--var',dest='assignments',action='append',default=[])
        sub.add_argument('--vars-file',type=Path)
        sub.add_argument('--timeout',type=positive_timeout,default=30)
        sub.add_argument('--budget',type=positive_timeout,default=90,help='shared command collection budget in seconds')
        if action=='query':
            sub.add_argument('--save',action='store_true',help='retain this manual observation and refresh configured consumers')
    dispatch = commands.add_parser('dispatch',description='Run due jobs only for explicitly enabled inventory.yaml hosts. Save attempts before connection; failures wait until next normal interval. No retries.',
                                   help='execute the due-work scheduler once')
    dispatch.add_argument('--dry-run',action='store_true',help='show due jobs without connection or writes')
    dispatch.add_argument('--timeout',type=positive_timeout,default=30)
    dispatch.add_argument('--budget',type=positive_timeout,default=90)
    dispatch.add_argument('--threads',type=int,default=4,help='concurrent hosts, 1–64; default 4')
    dispatch.add_argument('--quiet',action='store_true',help='suppress success output; durable observations/errors remain local')
    runs = commands.add_parser('runs', help='read durable observation runs without connecting')
    runs.add_argument('operation', choices=('list','show'))
    runs.add_argument('run_id', nargs='?')
    state = commands.add_parser('status',description='Read scheduler settings and last attempts without connecting or writing.',help='inspect settings and attempts')
    latest = commands.add_parser('latest',description='Query retained inventory as a mixed-age latest-attempt view per property. No connection or writes; failed values remain gaps.',help='read latest retained property attempts')
    latest.add_argument('--host',required=True)
    latest.add_argument('--recipe',default='system/inventory/overview')
    edit = commands.add_parser('configure',description='Enable/disable one scheduled host or override a job. Writes inventory.yaml only; no collection or cron changes.',
                               help='configure explicit host schedules and job overrides')
    edit.add_argument('--host')
    edit.add_argument('--recipe',default=None)
    edit.add_argument('--job')
    mode = edit.add_mutually_exclusive_group()
    mode.add_argument('--enable',action='store_true')
    mode.add_argument('--disable',action='store_true')
    edit.add_argument('--interval',type=schedule.interval)
    edit.add_argument('--defaults',action='store_true',help='edit a shared job default; requires --job and no --host')
    cron = commands.add_parser('cron',description='Show/install/remove this profile\'s marked entry in the current user crontab. Installation does not enable any host.',
                               help='manage the marked minute cron entry')
    cron.add_argument('operation',choices=('show','install','remove'))
    for sub in (desc,*[commands.choices[n] for n in ('query','run')],dispatch,state,latest,edit,cron,runs):
        sub.add_argument('--json',action='store_true',help='JSON output, including in terminals')
        if sub is not desc:
            env = sub.add_mutually_exclusive_group()
            env.add_argument('--root',type=Path)
            env.add_argument('--profile')
    args = parser.parse_args(argv)
    try:
        prepare_console(args.json)
        data = service.catalog()
        if args.command=='describe':
            result = data
            if args.job:
                if set(args.job)-set(data['jobs']):
                    raise ConfigError('unknown inventory job')
                result = dict(data,jobs={k:v for k,v in data['jobs'].items() if k in args.job},
                              properties={k:v for k,v in data['properties'].items() if v['job'] in args.job})
        else:
            root = resolve_root(args.root,args.profile)
            if args.command in ('query','run'):
                if args.command=='query' and not args.property and not args.job:
                    raise ConfigError('query requires --property or --job')
                if args.note and args.command=='query' and not args.save:
                    raise ConfigError('--note requires --save')
                result = service.collect_host(root,args.host,jobs=args.job,properties=args.property,
                    save=args.command=='run' or args.save, note=args.note,reference=args.recipe,
                    timeout=args.timeout,budget=args.budget,
                    cli_values=__import__('recipe_inputs').json_object(args.vars_file) if args.vars_file else None,
                    assignments=args.assignments)
            elif args.command=='runs':
                from observation_runs import list_runs, show
                if (args.operation == 'show') != bool(args.run_id):
                    raise ConfigError('runs show requires run_id; runs list excludes it')
                result = show(root,args.run_id) if args.run_id else {'runs':list_runs(root)}
            elif args.command=='dispatch':
                result = service.dispatch(root,dry_run=args.dry_run,timeout=args.timeout,budget=args.budget,threads=args.threads)
                if args.quiet:
                    return 0 if result['status'] in ('success','skipped') else 1
            elif args.command=='cron':
                # Validate the existing profile before installing an entry, without creating or enabling anything.
                service.profile(root)
                from inventory_cron import update
                result = update(root,args.operation)
            elif args.command=='latest':
                from retention_store import query
                records = query(root,hosts=[args.host],recipe=args.recipe,kind='observation')['records']
                result = {'status':'success','host_id':args.host,'groups':service.latest_groups(records),
                          'note':'Mixed-age latest attempts; consult each sample time and source observation. No interpolation.'}
            else:
                p = service.profile(root)
                settings = schedule.settings(root,data,p.hosts.list())
                if args.command=='status':
                    result = {'status':'success','settings':settings,'state':schedule.read_state(root)}
                else:
                    if not (args.enable or args.disable or args.interval is not None):
                        raise ConfigError('configure requires --enable, --disable or --interval')
                    if args.defaults:
                        if args.host or not args.job or args.recipe:
                            raise ConfigError('--defaults requires --job and excludes --host/--recipe')
                        target = settings.setdefault('defaults',{})
                    else:
                        if not args.host or args.host not in p.hosts.list():
                            raise ConfigError('configure requires a known --host')
                        host = settings.setdefault('hosts',{}).setdefault(args.host,{'enabled':False,'jobs':{}})
                        if args.recipe:
                            service.definition(p.hosts._config,args.recipe)
                            host['recipe'] = args.recipe
                        target = host.setdefault('jobs',{}) if args.job else None
                        if not args.job:
                            if args.interval is not None:
                                raise ConfigError('--interval requires --job')
                            host['enabled'] = args.enable
                    if args.job:
                        if args.job not in data['jobs']:
                            raise ConfigError('unknown inventory job')
                        options = target.setdefault(args.job,{})
                        if args.enable or args.disable:
                            options['enabled'] = args.enable
                        if args.interval is not None:
                            options['interval'] = args.interval
                    path = checked(root,'inventory.yaml')
                    atomic(path,canonical(settings)+'\n')
                    result = {'status':'success','settings':settings,'path':str(path)}
        # JSON is the stable utility contract. Human terminal views use the shared table helper.
        if sys.stdout.isatty() and not args.json:
            from console_output import table
            if args.command=='describe':
                print(table(['Property','Job','YANG node','Unit'],[(n,s['job'],s['yang_path'],s['unit']) for n,s in result['properties'].items()]))
            elif args.command in ('query','run'):
                print(table(['Group','Property','Entity','Value','State','Reason','Sample time'],
                    [(g['id'],s['property'],canonical(s['keys']),canonical(s['value']),s['status'],s.get('reason_code') or '',s['observed_at']) for g in result['groups'] for s in g['samples']]))
                print('Status:',result['status'],'Retention:',result.get('retention',{}).get('status','unknown'))
                print('Actor:',result['actor'].get('username') or 'unknown','Scope:',result['actor']['mode'])
                print('Identity:',result['identity_warning'])
                if result.get('result_path'):
                    print('Result:',result['result_path'])
            else:
                print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False))
        else:
            print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False))
        if args.command=='runs':
            return 0
        return 0 if result.get('status','success') in ('success','skipped') and result.get('retention',{}).get('status')!='failed' and result.get('content_update',{}).get('status')!='failed' else 1
    except (ConfigError,OSError,ValueError,ImportError,ConsoleDependencyError) as exc:
        print('ERROR: '+(str(exc) if isinstance(exc,(ConfigError,ConsoleDependencyError)) else type(exc).__name__),file=sys.stderr)
        return 1
