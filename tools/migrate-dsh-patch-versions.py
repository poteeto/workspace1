#!/usr/bin/env python3
"""Retarget *validated* runtime patch recipes to the exact DSH release.
Run only after tools/audit-dsh-patches.py has matched each active anchor.
Specialized patches have independent consumers and are intentionally excluded.
"""
from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]
assets=root/'app/src/main/assets'
registry=json.loads((assets/'runtime-patches.json').read_text())
version=json.loads((root/'tools/dsh-runtime/package.json').read_text())['dependencies']['@deepseek-ai/dsh']
if registry.get('dshVersion')!=version:raise ValueError('REGISTRY_TARGET_VERSION')
changed=[]
for entry in registry['active']:
    file=assets/entry['asset']
    spec=json.loads(file.read_text())
    if spec.get('dshVersion')==version:continue
    if spec.get('dshVersion')!='0.2.0-rc.2':raise ValueError('UNEXPECTED_PATCH_VERSION:'+entry['asset'])
    spec['dshVersion']=version
    file.write_text(json.dumps(spec,indent=2,ensure_ascii=False)+'\n')
    changed.append(entry['asset'])
print('Retargeted',len(changed),'validated active patch recipes:',', '.join(changed))
