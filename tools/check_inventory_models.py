"""Offline development check for bundled YANG paths, snapshots and JSON schemas.

Requires pyang 2.7.1 and jsonschema 4.25.1 in a Python 3.11-3.13 QA environment.
No host access, package installation or file writes.
"""
import hashlib
import json
from pathlib import Path
import runpy


def check():
    from pyang import context, repository, error
    from jsonschema import Draft202012Validator
    root = Path(__file__).resolve().parents[1]/'recipes/system/inventory/overview'
    catalog = json.loads((root/'collection.json').read_text())
    if catalog != runpy.run_path(str(root/'properties.py'))['catalog']():
        raise ValueError('generated catalog differs from property definitions')
    schema = json.loads((root/'job-retention.schema.json').read_text())
    Draft202012Validator.check_schema(schema)
    if schema['property_catalog'] != catalog:
        raise ValueError('retention schema does not bind current property definitions')
    sources = json.loads((root/'yang/SOURCE.json').read_text())
    count = 0
    for manifest in (root/'yang/SOURCE.json',root/'yang/openconfig/SOURCE.json'):
        for item in json.loads(manifest.read_text())['modules']:
            path = manifest.parent/(item['module']+'@'+item['revision']+'.yang')
            if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
                raise ValueError('public module digest mismatch: '+str(path))
            count += 1
    ctx = context.Context(repository.FileRepository(str(root/'yang')))
    for path in sorted((root/'yang').rglob('*.yang')) + [root/'opsfeast-inventory.yang']:
        ctx.add_module(path.name,path.read_text())
    ctx.validate()
    failures = [(str(pos),tag,args) for pos,tag,args in ctx.errors if error.is_error(error.err_level(tag))]
    if failures:
        raise ValueError(str(failures))
    def data_children(nodes):
        return [child for node in nodes for child in (data_children(getattr(node,'i_children',[])) if node.keyword in ('choice','case') else [node])]
    for name,spec in catalog['properties'].items():
        module = ctx.get_module(spec['module'],spec['revision'])
        if module is None or module.search_one('namespace').arg != spec['namespace']:
            raise ValueError('missing module/revision/namespace: '+name)
        for path in [spec['yang_path'],*spec.get('key_paths',{}).values()]:
            current = None
            children = ctx.get_module(path.split('/')[1].split(':')[0]).i_children
            for segment in path.split('/')[1:]:
                if ':' in segment:
                    owner,node = segment.split(':',1)
                else:
                    owner,node = None,segment
                matches = [child for child in data_children(children) if child.arg==node and (owner is None or child.i_module.arg==owner)]
                if len(matches)!=1:
                    raise ValueError('unresolved or ambiguous YANG path: '+name+' '+path)
                current = matches[0]
                children = getattr(current,'i_children',[])
            if current.keyword not in ('leaf','leaf-list','anydata'):
                raise ValueError('property/key must identify a value node: '+name)
    print('PASS:',len(catalog['properties']),'property paths;',count,'public snapshots; YANG modules and JSON Schema valid.')


if __name__=='__main__':
    check()
