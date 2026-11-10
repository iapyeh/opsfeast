"""Recipe-specific declarations and saved evidence; no collection on reads."""
import json
import sqlite3
from . import ConfigError
from .core import Instance
from .menu_preferences import inspect as preferences, MenuError
from .recipe_defaults import item_for, inspect as defaults


def inspect(product,*,profile,reference,offset=0,limit=5,host=None):
    selected=Instance.open(product).profile(profile)
    item=item_for(selected,reference)
    # Import the product facade, not recipe Python/normalizers.
    from .recipe_menu import menu
    card=next(row for row in menu(selected)['items'] if row['reference']==reference)
    from management_view import masked
    card={**card,'inputs':masked(card['inputs'])}
    definition=item['descriptor']
    declared={'inputs':masked(item.get('inputs',{})),'retention':(item.get('retention') or {}).get('declaration'),
              'output':definition.get('output',{}),'inventory':card.get('inventory_catalog')}
    saved={'status':'success','items':[],'total':0,'next_offset':None,'hosts':[]}
    from retention_store import settings
    if settings(selected.root) is None:saved.update(status='unavailable',reason_code='retention_namespace_not_initialized')
    else:
        try:
            rows=selected.retention.query(recipe=reference)['records']
            saved['hosts']=sorted({r['host_id'] for r in rows})
            if host:rows=[r for r in rows if r['host_id']==host]
            rows.sort(key=lambda r:(r['observed_at'],r['record_id']),reverse=True)
            saved['total']=len(rows)
            saved['next_offset']=offset+limit if len(rows)>offset+limit else None
            for row in rows[offset:offset+limit]:
                value=json.dumps(row['data'],ensure_ascii=False,indent=2)
                saved['items'].append({key:row.get(key) for key in ('record_id','host_id','namespace','observed_at','recipe_reference','recipe_id','origin')})
                saved['items'][-1].update(status=row['data'].get('status','unknown'),data_preview=value[:32768],data_truncated=len(value)>32768,
                                         recipe_version=row['data'].get('recipe_version'))
        except (ConfigError,OSError,ValueError,sqlite3.Error):saved.update(status='unavailable',reason_code='retention_read_failed')
    from recipe_reports import results
    available=results(selected.root,kind='report')
    reports={'status':available['status'],'items':[r for r in available['results'] if r['recipe_reference']==reference][:100]}
    operations=results(selected.root,kind='operation')
    attempts={'status':operations['status'],'items':[{k:r.get(k) for k in ('result_id','host_id','status','reason_code','started_at','retention','content_update')}
              for r in operations['results'] if r['recipe_reference']==reference][:10]}
    return {'schema_version':'0.1.0','profile':selected.name,'recipe':card,'declarations':declared,
            'defaults':defaults(product,profile=profile,reference=reference),'preferences':preferences(selected),
            'saved':saved,'reports':reports,'attempts':attempts}


def record(product,*,profile,reference,record_id):
    selected=Instance.open(product).profile(profile)
    item_for(selected,reference)
    row=selected.retention.show(record_id)
    if row['recipe_reference']!=reference:raise MenuError('record_does_not_belong_to_recipe')
    encoded=json.dumps(row,ensure_ascii=False,indent=2).encode()
    if len(encoded)>16*1024*1024:raise MenuError('record_exceeds_16_mib')
    return encoded
