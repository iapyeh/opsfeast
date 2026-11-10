"""Bounded original command streams, framed before PTY stream merging."""
import re
import copy
from datetime import datetime,timezone
from uuid import uuid4

MAX_OUTPUT = 262144


def bounded(text):
    return text.encode('utf-8')[:MAX_OUTPUT].decode('utf-8',errors='ignore')


def capture(actor, command, timeout, evidence):
    """Mutate evidence even on failure; return parser text and a capture error code.

    stderr is bounded inside command substitution, with a sentinel preserving its
    trailing newlines. No target files are created. The outer pipe bounds the
    combined transport. A random frame separates streams even through a PTY.
    """
    shared=getattr(actor,'inventory_probe_cache',None)
    key=(command,getattr(actor,'inventory_cache_scope',''))
    cacheable=shared is not None and command in ('cat /proc/meminfo','LC_ALL=C df -Pk','LC_ALL=C df -Pi')
    if cacheable and key in shared:
        evidence.update(copy.deepcopy(shared[key]));evidence['_captured_time']=True
        return evidence['stdout'].replace('\r\n','\n'),None
    token=uuid4().hex
    begin='__OPSFEAST_STDERR_'+token+'__'
    end='__OPSFEAST_END_'+token+'__'
    script=("( exec 3>&1; _ops_err=$( { " + command +
            "; printf '\\n__OPSFEAST_EXIT_%s\\n' \"$?\"; } 2>&1 1>&3 | head -c " +
            str(MAX_OUTPUT+1) + "; printf '.' ); _ops_err=${_ops_err%.}; " +
            "printf '"+begin+"\\n%s\\n"+end+"\\n' \"$_ops_err\" ) | head -c " + str(MAX_OUTPUT*2+512))
    evidence.update(stdout=None,stderr=None,stdout_truncated=False,stderr_truncated=False)
    def decode(result):
        output=getattr(result,'stdout','') or ''
        frame=re.search(r'\r?\n__OPSFEAST_EXIT_(\d+)\r?\n'+begin+r'\r?\n',output)
        tail=re.search(r'\r?\n'+end+r'\r?\n?$',output)
        if frame:
            evidence['stdout']=bounded(output[:frame.start()])
            evidence['stdout_truncated']=len(output[:frame.start()].encode())>MAX_OUTPUT
            evidence['exitcode']=int(frame[1])
        else:
            evidence['stdout']=bounded(output)
            evidence['stdout_truncated']=len(output.encode())>MAX_OUTPUT
        if frame and tail and tail.start()>=frame.end():
            error=output[frame.end():tail.start()]
            evidence['stderr']=bounded(error)
            evidence['stderr_truncated']=len(error.encode())>MAX_OUTPUT
        if getattr(result,'stdout_truncated',False):
            evidence['stdout_truncated']=True
        return bool(frame and tail and tail.start()>=frame.end())
    try:
        result=actor.exec_command(['/bin/sh','-c',script],check=False,command_timeout=timeout)
    except Exception as exc:
        if getattr(exc,'result',None) is not None:
            decode(exc.result)
        raise
    framed=decode(result)
    if evidence['stdout_truncated'] or evidence['stderr_truncated']:
        return None,'output_limit'
    if result.exitcode!=0:
        return None,'shell_failed'
    if not framed:
        return None,'producer_marker_missing'
    if cacheable and evidence.get('exitcode')==0:
        evidence['capture_id']=str(uuid4());evidence['observed_at']=datetime.now(timezone.utc).isoformat()
        shared[key]={k:copy.deepcopy(evidence[k]) for k in ('stdout','stderr','stdout_truncated','stderr_truncated','exitcode','started_at','observed_at','capture_id')}
        evidence['_captured_time']=True
    return evidence['stdout'].replace('\r\n','\n'),None
