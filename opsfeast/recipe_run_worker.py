"""One confirmed invocation in an owned process; uses the shared CLI executor."""
import json
from pathlib import Path
import sys

from . import ConfigError
from .recipe_runs import prepare_pair


def main():
    from recipe_cli import execute
    spec = json.loads(sys.stdin.buffer.read(131073))
    root = Path(spec['root']).resolve(strict=True)
    if 'batch' in spec:
        choices=[]
        for member in spec['batch']:
            pair,_=prepare_pair(root,member['reference'],spec['host'],member['vars'],member['inputs'],member.get('inventory_selection'))
            if pair['fingerprint']!=member['fingerprint']:raise ConfigError('recipe_preview_changed_review_again')
            choices.append({k:member[k] for k in ('reference','vars','inventory_selection') if k in member})
        from .routine_execution import run_host,update_children_content
        from observation_runs import start,record_result,finish,publish_execution
        from retention_store import refresh_content
        from recipe_runner import reporting,save_receipt
        run_id=start(root,[{'host_id':spec['host']}],'feast/meal',selection={'kind':'cli','all':False,'selectors':[['host',spec['host']]],'exclude':[]})
        result=None
        try:
            with reporting(True,'routine meal',host=spec['host']):
                result=run_host(root,spec['host'],choices,timeout=spec['timeout'],observation_run_id=run_id)
            record_result(root,run_id,spec['host'],result)
        finally:finish(root,run_id)
        content=refresh_content(root);code=0 if result['status']=='success' and content['status']!='failed' else 1
        _,content=publish_execution(root,run_id,code,content);result['content_update']=content
        update_children_content(root,result,content);save_receipt(Path(result['result_path']),result)
        print(json.dumps({k:result[k] for k in ('status','reason_code','result_path','children','meal_run_id','retention','content_update','observation_run_id')}))
        return code
    pair, inputs = prepare_pair(root, spec['reference'], spec['host'], spec['vars'], spec['inputs'], spec.get('inventory_selection'))
    if pair['fingerprint'] != spec['fingerprint']:
        raise ConfigError('recipe_preview_changed_review_again')
    invocation = {'targets': [('host', spec['host'])] if spec['host'] is not None else [],
                  'all': False, 'exclude': [], 'threads': None, 'timeout': spec['timeout'],
                  'assignments': [], 'vars_file': None, 'inputs': inputs, 'verbose': True, 'quiet': False}
    return execute(root, {'recipe': spec['reference'], 'invocation': invocation},
                   json_output=True, variables=spec['vars'], inventory_selection=spec.get('inventory_selection'))


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({'status': 'failed', 'reason_code': 'recipe_worker_failure', 'error_type': type(exc).__name__}))
        raise SystemExit(1)
