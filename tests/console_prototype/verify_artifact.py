"""Fail closed if a same-version published package or stale candidate is substituted."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import zipfile
import sshscript


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel',required=True,type=Path)
    parser.add_argument('--source',required=True,type=Path,help='read-only flat SSHScript source checkout')
    parser.add_argument('--sha256',required=True)
    args=parser.parse_args()
    digest=hashlib.sha256(args.wheel.read_bytes()).hexdigest()
    if digest!=args.sha256: raise SystemExit('Artifact changed: rebuild/review required; do not substitute PyPI')
    package=Path(sshscript.__file__).resolve().parent
    checked=[]
    with zipfile.ZipFile(args.wheel) as archive:
        for name in archive.namelist():
            if name.startswith('sshscript/') and name.endswith(('.py','.pyi')):
                raw=archive.read(name)
                if raw!=(args.source/Path(name).name).read_bytes():
                    raise SystemExit('Source drift: rebuild required: '+name)
                if raw!=(package/Path(name).name).read_bytes():
                    raise SystemExit('Imported artifact mismatch: '+name)
                checked.append(name)
    print(json.dumps({'sha256':digest,'checked_modules':len(checked),'interpreter':sys.executable,
                      'module_path':sshscript.__file__,'distribution_version':importlib.metadata.version('sshscript'),
                      'source_commit':subprocess.check_output(['git','-C',str(args.source),'rev-parse','HEAD'],text=True).strip()},indent=2))

if __name__=='__main__': main()
