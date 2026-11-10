"""Adapt synthetic framed-probe actors to the new owned identity/phase boundary."""
from contextlib import contextmanager
from types import SimpleNamespace

class IdentityActor:
    def __init__(self,actor):self.actor=actor;self.uid=1000;self.user='synthetic'
    def exec_command(self,argv,**kwargs):
        if argv==['id','-un']:return SimpleNamespace(stdout=self.user+'\n',stderr='',exitcode=0)
        if argv[:2]==['id','-u']:return SimpleNamespace(stdout=str(self.uid)+'\n',stderr='',exitcode=0)
        if argv==['uname','-s']:
            result=self.actor.exec_command(['/bin/sh','-c','uname -s'],**kwargs)
            return SimpleNamespace(stdout=result.stdout.split('__OPSFEAST_EXIT_')[0].strip()+'\n',stderr=result.stderr,exitcode=127 if '__OPSFEAST_EXIT_127' in result.stdout else result.exitcode)
        return self.actor.exec_command(argv,**kwargs)

@contextmanager
def connection(actor,*args):
    adapted=IdentityActor(actor)
    args[-1]['connected']=True
    yield adapted

@contextmanager
def root(session,config,host,timeout,evidence,**kwargs):
    session.uid=0;session.user='root';evidence['status']='success'
    try:yield session
    finally:session.uid=1000;session.user='synthetic';evidence['restoration_verified']=True
