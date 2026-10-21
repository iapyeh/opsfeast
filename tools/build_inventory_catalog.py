"""Regenerate the trusted inventory catalog, schema and extension module offline.

Run explicitly after editing recipe properties.py, then run check_inventory_models.py.
No target connections, downloads, package installations or user-data edits.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import runpy,json


def main():
    root=Path(__file__).resolve().parents[1]/'recipes/system/inventory/overview'
    catalog=runpy.run_path(str(root/'properties.py'))['catalog']()
    (root/'collection.json').write_text(json.dumps(catalog,indent=2)+'\n')
    keys=['contract_version','observation_id','source_id','recipe_id','recipe_version','host_id','status','trigger','note','definition_sha256','started_at','observed_at','actor','groups','probes','identity_warning','property_definitions','implementation','execution_errors']
    sample={'type':'object','additionalProperties':False,'required':['property','keys','value','status','reason_code','observed_at','source_id'],'properties':{'property':{'enum':list(catalog['properties'])},'status':{'enum':['success','unavailable']},'keys':{'type':'object'},'value':{},'reason_code':{'type':['string','null']},'observed_at':{'type':'string'},'source_id':{'type':'string'}}}
    group={'type':'object','additionalProperties':False,'required':['id','title','started_at','observed_at','status','samples','coverage'],'properties':{'id':{'enum':list(catalog['jobs'])},'title':{'type':'string'},'started_at':{'type':'string'},'observed_at':{'type':'string'},'status':{'enum':['success','partial','failed']},'samples':{'type':'array','items':sample},'coverage':{'type':'array','items':{'type':'object'}}}}
    schema={'$schema':'https://json-schema.org/draft/2020-12/schema','title':'Inventory job observations 0.1.0','description':'Per-group samples with immutable source times, failures and model identity. Not an online health assertion.','type':'object','additionalProperties':False,'property_catalog':catalog,'required':keys,'properties':{k:{'type':'string'} for k in keys}}
    schema['properties'].update(contract_version={'const':'0.1.0'},recipe_id={'const':'inventory-system'},status={'enum':['success','partial','failed']},trigger={'enum':['manual','scheduled']},actor={'type':'object'},groups={'type':'array','minItems':1,'maxItems':11,'items':group},probes={'type':'array','maxItems':256,'items':{'type':'object'}},property_definitions={'type':'object'},implementation={'type':'object'})
    schema['properties']['probes']['items']['properties'] = {'stdout': {'type': ['string', 'null'], 'description': 'Original captured stdout, null when unavailable. UTF-8 byte bound enforced by semantic validator.'}, 'stderr': {'type': ['string', 'null'], 'description': 'Original captured stderr, separated before any PTY stream merging.'}, 'stdout_truncated': {'type': 'boolean'}, 'stderr_truncated': {'type': 'boolean'}}
    schema['$comment'] = 'Last modified: '+datetime.now(ZoneInfo('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S')
    schema['properties']['execution_errors'] = {'type':'array','items':{'type':'object'}}
    (root/'job-retention.schema.json').write_text(json.dumps(schema,indent=2)+'\n')
    tree={}
    for spec in catalog['properties'].values():
        if spec['module']!='opsfeast-inventory':continue
        node=tree
        parts=spec['yang_path'].split('/')[2:]
        for part in parts[:-1]:node=node.setdefault(part,{})
        node[parts[-1]]=spec
    lists={'storage/filesystems','storage/block-devices','storage/inodes','network/interfaces'}
    lines=['module opsfeast-inventory {','  yang-version 1.1;','  namespace "urn:opsfeast:yang:inventory";','  prefix ofinv;','  organization "OpsFeast contributors";','  description "Inventory extensions without an exact selected standard node. Read-only observations; provenance is in the observation envelope.";','  revision 2026-10-20 { description "Initial grouped inventory definitions."; }','  container inventory {','    config false;','    description "Collected extension properties.";']
    def emit(nodes,path='',indent='    '):
        for name,value in nodes.items():
            current=(path+'/'+name).strip('/')
            if isinstance(value,dict) and 'yang_path' in value:
                desc=value['description'].replace('"','\\"')
                if value['type']=='array':lines.extend([indent+'anydata '+name+' {',indent+'  description "'+desc+'";',indent+'}'])
                else:
                    typ={'integer':'uint64','number':'decimal64','string':'string'}[value['type']]
                    lines.append(indent+'leaf '+name+' {')
                    lines.append(indent+'  type '+typ+(' { fraction-digits 6; }' if typ=='decimal64' else ';'))
                    if value['unit']:lines.append(indent+'  units "'+value['unit']+'";')
                    lines.extend([indent+'  description "'+desc+'";',indent+'}'])
            else:
                lines.extend([indent+('list ' if current in lists else 'container ')+name+' {',indent+'  description "'+name.replace('-',' ')+' observations.";'])
                emit(value,current,indent+'  ')
                lines.append(indent+'}')
    emit(tree)
    lines.extend(['  }','}'])
    (root/'opsfeast-inventory.yang').write_text('\n'.join(lines)+'\n')
    print('Generated:',len(catalog['properties']),'properties')


if __name__ == "__main__":
    main()
