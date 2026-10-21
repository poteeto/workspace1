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
