"""Descriptive Recipe composition and execution gaps, never candidate execution."""
from pathlib import Path


def describe(directory, metadata, report, *, runnable):
    resources=metadata.get('resources') or {}
    titles=metadata.get('resource_titles') or {}
    runner=metadata.get('runner') or {}
    inputs=metadata.get('inputs') if isinstance(metadata.get('inputs'),dict) else {}
    output=metadata.get('output') if isinstance(metadata.get('output'),dict) else {}
    directory=Path(directory)
    disk=[]
    def include(path):
        try:
            name=path.relative_to(directory).as_posix()
            if any(part.startswith('.') or part=='__pycache__' for part in path.relative_to(directory).parts):return
            if name not in resources and name not in disk and not path.is_symlink() and path.resolve().is_relative_to(directory.resolve()) and path.is_file():
                disk.append(name)
        except (OSError,ValueError):pass
    for name in ('flow.plan.md','plan.md','README.md','readme.md','requirements.lock','requirements.txt'):
        include(directory/name)
    if isinstance(runner.get('entrypoint'),str):include(directory/runner['entrypoint'])
    for folder in ('contracts','routines','scripts','schemas','tests','conformance','resources'):
        base=directory/folder
        if base.is_symlink() or not base.is_dir():continue
        for index,path in enumerate(base.rglob('*')):
            if index>=200 or len(disk)>=50:break
            include(path)
    components=[];assigned=set()
    def component(identifier, names=(), *, files=(), fields=(), present=False, required=False):
        names=list(names);assigned.update(names)
        files=list(files)
        components.append({'id':identifier,'required_for_execution':required,
                           'state':'provided' if names else 'file_present' if files else 'declared' if present else 'missing',
                           'resources':[{'path':name,'title':titles.get(name,'')} for name in names],
                           'files':files,
                           'fields':list(fields)})
    def matching(*prefixes, exact=()):
        return [name for name in resources if name in exact or name.startswith(prefixes)]
    def disk_matching(*prefixes,exact=()):return [name for name in disk if name in exact or name.startswith(prefixes)]
    component('plan',matching(exact=('flow.plan.md','plan.md')),files=disk_matching(exact=('flow.plan.md','plan.md')))
    component('step_contracts',matching('contracts/'),files=disk_matching('contracts/'))
    component('utilities',matching('routines/'),files=disk_matching('routines/'),fields=('runner.routines',),present=bool(runner.get('routines')),required=runner.get('contract')=='python-routines')
    component('execution',matching('scripts/'),fields=('runner.contract','runner.entrypoint'),
              files=disk_matching('scripts/',exact=(runner.get('entrypoint'),)),present=bool(runner.get('entrypoint')) or runnable,required=True)
    variables=inputs.get('variables') if isinstance(inputs.get('variables'),dict) else {}
    component('inputs',fields=('inputs.variables',),present=bool(variables),required=any(isinstance(spec,dict) and spec.get('required') is True for spec in variables.values()))
    component('outputs',matching('schemas/'),files=disk_matching('schemas/'),fields=('output.schema_version',),
              present=bool(output.get('schema_version')),required=metadata.get('id')!='inventory-system')
    component('verification',matching('conformance/','tests/'),files=disk_matching('conformance/','tests/'),fields=('verification',),present=bool(metadata.get('verification')))
    component('dependencies',matching(exact=('requirements.lock','requirements.txt')),files=disk_matching(exact=('requirements.lock','requirements.txt')),fields=('dependencies',),present=bool(metadata.get('dependencies')))
    component('permissions',fields=('access_mode','permissions','side_effects'),
              present=bool(metadata.get('permissions') or metadata.get('side_effects') or metadata.get('access_mode') in ('read','write')),required=runner.get('contract') in ('python-routines','recipe-meal'))
    component('guide',matching(exact=('README.md','readme.md')),files=disk_matching(exact=('README.md','readme.md')))
    component('assets',[name for name in resources if name not in assigned],files=disk_matching('resources/'))
    blockers=[]
    if not runnable:
        if not runner.get('contract') and metadata.get('id')!='inventory-system':
            blockers.append({'code':'runner_contract_missing','field':'runner.contract'})
        elif runner.get('contract') and not runner.get('version'):
            blockers.append({'code':'runner_version_missing','field':'runner.version'})
        entry=runner.get('entrypoint')
        if not entry and metadata.get('id')!='inventory-system':
            blockers.append({'code':'entrypoint_missing','field':'runner.entrypoint'})
        elif entry:
            candidate=Path(directory)/str(entry)
            if not candidate.resolve().is_relative_to(Path(directory).resolve()) or not candidate.is_file():
                blockers.append({'code':'entrypoint_unavailable','field':'runner.entrypoint'})
        if not metadata.get('version'):
            blockers.append({'code':'version_missing','field':'version'})
        if not metadata.get('descriptor_version'):
            blockers.append({'code':'descriptor_version_missing','field':'descriptor_version'})
        if not output.get('schema_version') and metadata.get('id')!='inventory-system':
            blockers.append({'code':'output_schema_missing','field':'output.schema_version'})
        if report['errors']:
            blockers.append({'code':'static_validation_failed','field':'','errors':list(report['errors'])})
    return {'components':components,'execution_blockers':blockers}
