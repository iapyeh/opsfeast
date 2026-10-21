"""Synthetic wire frames for the inventory command-stream collector."""
import re


def framed(script, stdout, stderr=""):
    match=re.search(r'__OPSFEAST_STDERR_([0-9a-f]{32})__',script)
    if not match:
        return stdout
    token=match[1]
    return stdout+'__OPSFEAST_STDERR_'+token+'__\n'+stderr+'\n__OPSFEAST_END_'+token+'__\n'
