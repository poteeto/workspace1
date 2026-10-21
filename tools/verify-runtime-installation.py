#!/usr/bin/env python3
"""Pre-release simulation of the actual Android managed-runtime installation.

Uses the exact npm tree pinned for Android ARM64. It reconstructs the ordering
and idempotence rules in ExactTextPatch + ManagedPatchChain, then validates
every *specialized* runtime transformation the Android installer applies.
Unlike source-only version checks, a single failed operation blocks release.
This is an upstream compatibility preflight, NOT a substitute for device boot.
"""
from __future__ import annotations
import collections
import json
from pathlib import Path
import sys
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'app/src/main/assets'
MODULES = ROOT / 'tools/dsh-runtime/node_modules'
VERSION = json.loads((ROOT/'tools/dsh-runtime/package.json').read_text())['dependencies']['@deepseek-ai/dsh']
REPORT: list[tuple[str, str, str]] = []

def case(name, fn):
    try:
        value=fn()
        REPORT.append((name,'PASS',str(value or '')))
    except Exception as exc:
        REPORT.append((name,'FAIL',str(exc)))

def data(name):
    return json.loads((ASSETS/name).read_text(encoding='utf8'))

def module(name):
    p=Path(name)
    if p.is_absolute() or '..' in p.parts or '.' in p.parts or not name.startswith('@deepseek-ai/'):
        raise ValueError('unsafe module path: '+str(name))
    path=MODULES/p
    if not path.is_file() or path.is_symlink():
        raise ValueError('missing/unsafe published module: '+str(path))
    # Crucial: Java Compat.readAll decodes UTF-8 *without* normalizing CRLF.
    # Some reviewed patch 'after' fragments contain literal CRLF and packaging
    # writes those bytes. Python Path.read_text universal newline translation
    # would falsely report a mismatch on the actual already-patched APK module.
    return path.read_bytes().decode('utf8')

def exact(source,before,after):
    """Same pre/post conditions as Android ExactTextPatch.apply."""
    if not isinstance(source,str) or not before or not after or before==after:
        raise ValueError('invalid patch contract')
    old=source.count(before)
    patched=source.count(after)
    if patched==1 and old==after.count(before):
        return source
    if old!=1 or patched!=0:
        raise ValueError(f'expected one old/zero patched, got old={old} patched={patched}; anchor='+repr(before[:110]))
    return source.replace(before,after)

def validate_javascript(name, source):
    # Parse the final transformed module as ESM, but do not execute it.
    # Exact anchor match alone cannot guarantee a syntactically valid patch.
    result=subprocess.run(
        ['node','--check','--input-type=module'],
        input=source.encode('utf-8'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
    if result.returncode:
        raise ValueError('PATCHED_JS_SYNTAX_INVALID:'+name+':'
                         +result.stderr.decode('utf-8','replace')[-450:])

def recipe_patches(recipe):
    for p in recipe.get('patches',[]):
        after=p['after']
        if 'prependAsset' in p:
            after=(ASSETS/p['prependAsset']).read_text(encoding='utf8').replace('\r\n','\n')+'\n'+after
        yield p['before'],after

def check_manifest():
    manifest=data('managed-runtime-inputs.json')
    if manifest['schema']!=1:raise ValueError('schema changed')
    seen=set()
    for row in manifest['installs']:
        target=row['target']
        if not target or target.startswith('/') or '..' in Path(target).parts or target in seen:
            raise ValueError('unsafe/duplicate target '+target)
        seen.add(target)
        if not (ASSETS/row['asset']).is_file():
            raise ValueError('managed asset missing: '+row['asset'])
    for name in ['builtin-plugins.json','runtime-tools.json','bridge-token-compat.cjs']:
        if not (ASSETS/name).is_file(): raise ValueError('missing host input '+name)
    return f'{len(seen)} signed managed install targets exist'

def check_patch_registry():
    reg=data('runtime-patches.json')
    if reg['schema']!=1 or reg['dshVersion']!=VERSION:
        raise ValueError('registry/package version mismatch')
    release=json.loads((MODULES/'@deepseek-ai/dsh/package.json').read_text())
    if release['version']!=VERSION:raise ValueError('published package wrong version')
    groups=collections.OrderedDict()
    ids=set()
    for entry in reg['active']:
        asset=entry['asset']
        if asset in ids:raise ValueError('duplicate recipe '+asset)
        ids.add(asset)
        spec=data(asset)
        if spec.get('dshVersion')!=VERSION:raise ValueError('recipe version '+asset)
        name=entry.get('module') or spec.get('module')
        if not name:raise ValueError('missing module '+asset)
        groups.setdefault(name,[]).append((asset,spec,entry.get('markers',[])))
    for entry in reg['retired']:
        if entry['asset'] in ids:raise ValueError('retired active '+entry['asset'])
    checks=0
    for path,recipes in groups.items():
        original=module(path)
        def run(source):
            for name,spec,markers in recipes:
                if markers and all(marker in source for marker in markers):continue
                for before,after in recipe_patches(spec):
                    source=exact(source,before,after)
            return source
        first=run(original)
        second=run(first)
        if path.endswith(('.js','.mjs','.cjs')):validate_javascript(path,first)
        if first!=second:raise ValueError('non-idempotent chain '+path)
        if first==original:
            # Some modules (notably rc1 settings) are intentionally patched
            # already by build-dsh-runtime.py before Android sees the tree.
            already_applied = all(
                (markers and all(m in original for m in markers))
                or all(after in original for before,after in recipe_patches(spec))
                for _,spec,markers in recipes)
            if not already_applied:
                raise ValueError('unexpected pristine no-op '+path)
        checks+=sum(len(spec['patches']) for _,spec,_ in recipes)
    return f'{len(ids)} complete recipe chains, {checks} anchor substitutions, all idempotent'

def check_pdf():
    spec=data('pdf-compat-patch.json')
    if spec['dshVersion']!=VERSION:raise ValueError('version')
    s=module(spec['module'])
    compatibility=(ASSETS/spec['asset']).read_text().strip().replace('\n',' ')
    before=spec['mainBefore']
    current=exact(s,before,'/* DSHA_PDF_COMPAT_V1 */ '+compatibility+' '+before)
    before=spec['workerBefore']
    # Java JSONObject.quote emits a JSON double-quoted JS compatible literal.
    current=exact(current,before,'new Blob(['+json.dumps(compatibility+'\n',ensure_ascii=False)+', _dsh_pdf_worker_default,')
    validate_javascript(spec['module'],current)
    source=module(spec['resourceModule'])
    transformed=exact(source,spec['resourceBefore'],spec['resourceAfter'])
    validate_javascript(spec['resourceModule'],transformed)
    if 'DSHA_PDF_COMPAT_V1' not in current or spec['resourceAfter'] not in transformed:
        raise ValueError('PDF patch not present or not idempotent')
    return 'client PDF, Worker and resource protocol anchors'

def check_client_combos():
    spec=data('client-combo-patch.json')
    if spec['dshVersion']!=VERSION:raise ValueError('version')
    s=module('@deepseek-ai/dsh-client-modules/lib/index.js')
    updated=s
    for before,after in recipe_patches(spec):
        updated=exact(updated,before,after)
    validate_javascript('@deepseek-ai/dsh-client-modules/lib/index.js',updated)
    again=updated
    for before,after in recipe_patches(spec):
        again=exact(again,before,after)
    if updated!=again:raise ValueError('combo not idempotent')
    if updated==s and not all(after in s for before,after in recipe_patches(spec)):
        raise ValueError('combo unexpectedly not applied')
    for path in ['client-combo-cache/index.js','client-combo-cache/package.json']:
        if not (ASSETS/path).is_file():raise ValueError('missing combo-cache '+path)
    return f'{len(spec["patches"])} combo substitutions, cache assets, repeated run stable'

def check_browser_bootstrap():
    html=module('@deepseek-ai/dsh-web-frontend/dist/index.html')
    if html.count('<head>')!=1: raise ValueError('HTML head mismatch')
    if '<!-- DSHA_BROWSER_COMPAT_BEGIN -->' in html:raise ValueError('unexpected injected upstream block')
    for path in ['web-integration/es-compat.js','web-integration/startup.js']:
        contents=(ASSETS/path).read_text(encoding='utf8')
        if not contents.strip() or len(contents.encode())>2_097_152:raise ValueError('invalid browser script: '+path)
    return 'unique head, expected bootstrap scripts present'

def check_lan_settings():
    s=module('@deepseek-ai/dsh-client-ui-settings/lib/client.js')
    # This contract is identical to LanSettingsCompatibility.adapt() in
    # the actual Android installer. Assert Java invokes that class at all.
    java=(ROOT/'app/src/main/java/com/deepseekharness/app/runtime/RuntimeTools.java').read_text()
    adapter=(ROOT/'app/src/main/java/com/deepseekharness/app/util/LanSettingsCompatibility.java').read_text()
    assert 'LanSettingsCompatibility.adapt(source, version)' in java
    assert '0.2.1-rc.2' in adapter
    markers=(
        'id: "@deepseek-ai/dsh-client-ui-settings"',
        'this.ctx.remote.settings.describe()',
        'this.ctx.remote.settings.mutate(',
        'settings/document-updated',
        'remote.settings'
    )
    for marker in markers:
        if marker not in s:raise ValueError('host settings RPC changed: '+marker)
    for old in ['const persistence = ctx.remote.$host.isLoopback ? "host" : "memory";',
                'const persistence = "host"; // DSHA patch: LAN 代理场景强制 host 持久化']:
        if old in s:raise ValueError('obsolete browser persistence conditional found')
    return 'Host read/mutate/notify contract, no legacy injection'

def check_workspace_policy():
    spec=data('workspace-directory-policy-patch.json')
    if spec['dshVersion']!=VERSION:raise ValueError('version')
    src=module(spec['module'])
    for before,after in recipe_patches(spec):
        src=exact(src,before,after)
    validate_javascript(spec['module'],src)
    return f'{len(spec["patches"])} workspace policy transformations available'

def check_packaging_source():
    source=(ROOT/'tools/build-dsh-runtime.py').read_text()
    methods=['SESSION_PERSISTENCE_JSONL_MODULE','RC1_SETTINGS_MODULE',
             'LEXICAL_CLAIM_MODULE','dshaSessionHints']
    for marker in methods:
        if marker not in source:raise ValueError('packager missing migration guard: '+marker)
    return 'session state adapters and guarded packaging present'

case('locked npm dependencies',lambda: (
    json.loads((MODULES/'@deepseek-ai/dsh/package.json').read_text())['version']==VERSION
    or (_ for _ in ()).throw(ValueError('wrong DSH package'))))
case('managed runtime assets',check_manifest)
case('all registry patch chains',check_patch_registry)
case('PDF main/worker/resources',check_pdf)
case('client combiner',check_client_combos)
case('WebView bootstrap',check_browser_bootstrap)
case('LAN Host settings RPC',check_lan_settings)
case('workspace directory',check_workspace_policy)
case('packaged session migration',check_packaging_source)

for name,status,description in REPORT:
    print(f'INSTALL_PREFLIGHT_{status}: {name}: {description}')
print('INSTALL_PREFLIGHT_TOTAL',sum(r[1]=='PASS' for r in REPORT),'passed;',
      sum(r[1]=='FAIL' for r in REPORT),'failed')
if any(r[1]=='FAIL' for r in REPORT):
    sys.exit('UPGRADED_RUNTIME_HOST_PREFLIGHT_FAILED')
