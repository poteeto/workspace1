#!/usr/bin/env python3
"""Diagnostic stage for every upgrade: compare Android host patch assumptions
with the exact published DSH package bytes (not the old baseline).
"""
import json
from pathlib import Path
import sys

root=Path(__file__).resolve().parents[1]
deps=root/'tools/dsh-runtime/node_modules'
settings=deps/'@deepseek-ai/dsh-client-ui-settings/lib/client.js'
print('DSH version',json.loads((root/'tools/dsh-runtime/package.json').read_text())['dependencies']['@deepseek-ai/dsh'])
if not settings.is_file():
    raise SystemExit('DSH_SETTINGS_MODULE_NOT_FOUND')
code=settings.read_text()
patterns=[
 'const persistence = ctx.remote.$host.isLoopback ? "host" : "memory";',
 'const persistence = "host"; // DSHA patch: LAN 代理场景强制 host 持久化',
 'persistence', 'isLoopback', 'localStorage', 'sessionStorage', 'remote.$host'
]
for p in patterns:
    offsets=[];start=0
    while True:
        i=code.find(p,start)
        if i<0:break
        offsets.append(i);start=i+len(p)
    print('SETTINGS_ANCHOR',repr(p),'occurrences',len(offsets))
    for i in offsets[:8]:
        print(' ',repr(code[max(0,i-190):min(len(code),i+260)]))
print('SETTINGS_SOURCE',len(code),'bytes')

print('SETTINGS_CLIENT_HEAD',repr(code[:1700]))
for term in ('storage','Storage','persist','Persist','context','settings','Settings','save','Save','remote','Remote','schema','Schema'):
    offsets=[];start=0
    while True:
        at=code.find(term,start)
        if at<0:break
        offsets.append(at);start=at+len(term)
    print('SETTINGS_RELATED_TOKEN',term,len(offsets))
    for off in offsets[:7]:
        print(' ',repr(code[max(0,off-95):min(len(code),off+180)]))
print('FIND_SETTINGS_PERSISTENCE_ACROSS_ALL_PUBLISHED_MODULES')
patterns=('isLoopback ? "host"','const persistence =','persistence: "host"','localStorage','sessionStorage','persistence =','settingsStorage')
scoped=deps/'@deepseek-ai'
results=[]
for path in scoped.glob('*/lib/*.js'):
    try:
        if path.stat().st_size>1500000:continue
        source=path.read_text(errors='replace')
    except OSError:continue
    matches=[(p,source.find(p)) for p in patterns if p in source]
    if matches:
        results.append((path.relative_to(deps).as_posix(),[(term,source[max(0,i-85):i+210]) for term,i in matches]))
for path,match in results[:55]:
    print('CROSS_MODULE_STORAGE',path,repr(match))
print('CROSS_MODULE_COUNT',len(results))
