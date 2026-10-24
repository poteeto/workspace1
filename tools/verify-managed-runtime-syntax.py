#!/usr/bin/env python3
"""Parse every signed Android-managed runtime input without running its code.

Run after source-pinned generators and before APK packaging. This catches
syntax errors in the *exact* JS/Python/JSON/shell bytes the Android host will
install; it does not execute untrusted source or claim successful device boot.
"""
from __future__ import annotations
import argparse
import ast
import json
from pathlib import Path
import subprocess
import sys

parser=argparse.ArgumentParser()
parser.add_argument('--source-only',action='store_true',help='In lightweight npm audit, defer specifically generated binary assets to full APK CI')
args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'app/src/main/assets'
MANIFEST=json.loads((ASSETS/'managed-runtime-inputs.json').read_text())
paths={item['asset'] for item in MANIFEST['installs']}
paths.update(MANIFEST.get('assetFiles',[]))
for directory in MANIFEST.get('assetTrees',[]):
    folder=ASSETS/directory
    if not folder.is_dir() or folder.is_symlink():raise SystemExit('ASSET_TREE_NOT_DIRECTORY:'+directory)
    for p in folder.rglob('*'):
        if p.is_file():paths.add(p.relative_to(ASSETS).as_posix())
count=dict(json=0,python=0,js=0,shell=0,unchecked=0)
GENERATED_ARCHIVES={'offline-rootfs.bin','dsh-runtime.bin','ubuntu-tools.bin'}
deferred=[]
errors=[]
for name in sorted(paths):
    path=ASSETS/name
    if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(ASSETS.resolve()):
        if args.source_only and name in GENERATED_ARCHIVES and not path.exists():
            deferred.append(name)
            continue
        errors.append('MISSING_OR_UNSAFE:'+name)
        continue
    suffix=path.suffix.lower()
    try:
        if suffix=='.json':
            json.loads(path.read_text(encoding='utf-8'))
            count['json']+=1
        elif suffix=='.py':
            ast.parse(path.read_bytes().decode('utf-8'),filename=name)
            count['python']+=1
        elif suffix in ('.mjs','.cjs','.js'):
            data=path.read_bytes()
            mode='module' if suffix in ('.mjs','.js') else 'commonjs'
            command=['node','--check','--input-type='+mode]
            result=subprocess.run(command,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
            if result.returncode:
                raise ValueError(result.stderr.decode('utf8','replace')[:420])
            count['js']+=1
        elif suffix=='.sh':
            result=subprocess.run(['bash','-n',str(path)],capture_output=True,timeout=10)
            if result.returncode:
                raise ValueError(result.stderr.decode('utf8','replace')[:420])
            count['shell']+=1
        else: count['unchecked']+=1
    except (SyntaxError,ValueError,UnicodeError,OSError,subprocess.TimeoutExpired) as exc:
        errors.append(name+': '+str(exc))
if deferred:
    print('GENERATED_BINARY_ARCHIVES_DEFERRED_TO_FULL_APK_CI',','.join(sorted(deferred)))
for kind,n in count.items():
    print('SIGNED_ASSET_SYNTAX_COUNT',kind,n)
for message in errors[:30]:print('SIGNED_ASSET_SYNTAX_FAIL',message)
if errors:raise SystemExit('SIGNED_RUNTIME_ASSET_SYNTAX_INVALID:'+str(len(errors)))
print('SIGNED_RUNTIME_ASSET_SYNTAX_PASS',sum(count.values()),'source files inspected')
