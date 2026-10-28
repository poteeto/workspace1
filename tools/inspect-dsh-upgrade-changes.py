#!/usr/bin/env python3
"""Brief diagnostic excerpts for DSH mobile patch migrations; no secrets."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
base=ROOT/'tools/dsh-runtime/node_modules/@deepseek-ai'
for label,relative,needles in [
 ('Plugin manager','dsh-client-ui-plugin-manager/lib/client.js',['installBundle','enabled:']),
 ('Tool policy','dsh-tools/lib/index.js',['cordis','super(ctx, "tools")','captureExecution','deferredContexts.set','guardReason','bodyInvoked','ToolNotFoundError']),
 ('Web front','dsh-web-frontend/dist/index.html',['index-']),
]:
    f=base/relative
    print('==',label,relative,'exists=',f.exists())
    if not f.exists():continue
    lines=f.read_text().splitlines()
    seen=set()
    for i,line in enumerate(lines):
        if any(k in line for k in needles):
            for j in range(max(0,i-3),min(len(lines),i+4)):
                if j not in seen:
                    print(f'{j+1}: {lines[j][:270]}');seen.add(j)
            if len(seen)>95:break
print('== Front-end dist files')
for f in sorted((base/'dsh-web-frontend/dist/assets').glob('index-*.js')):
    data=f.read_text()
    print(f.name,'length',len(data),'tooltip markers',data.count('useCallback'),data.count('pointerdown'))
    for needle in ('se=j.useCallback','visibilitychange','scroll', 'tooltip'):
        ix=data.find(needle)
        if ix>=0:print('  ',needle,repr(data[max(0,ix-120):ix+210]))
