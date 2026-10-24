#!/usr/bin/env python3
"""Verify PDF companion patch anchors against the exact npm release."""
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
assets=root/'app/src/main/assets'
modules=root/'tools/dsh-runtime/node_modules'
pdf=json.loads((assets/'pdf-compat-patch.json').read_text())
checks={
    'pdf-main':(pdf['module'],pdf['mainBefore']),
    'pdf-worker':(pdf['module'],pdf['workerBefore']),
    'resource':(pdf['resourceModule'],pdf['resourceBefore']),
}
failed=[]
for name,(module,anchor) in checks.items():
    file=modules/module
    if not file.exists():
        print('MISSING',name,module)
        failed.append(name)
        continue
    text=file.read_text()
    count=text.count(anchor)
    print('PDF_ANCHOR',name,'count',count,'module',module)
    if count!=1:failed.append(name)
if failed:raise SystemExit('PDF_PATCH_UPSTREAM_CHANGED:'+','.join(failed))
print('PDF_PATCH_ANCHORS_VERIFIED')
