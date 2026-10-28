#!/usr/bin/env python3
"""Verify the *actual compressed DSH payload* against Android install semantics.

The earlier preflight checks pristine npm packages; this test also extracts all
APK-critical JS and JSON from the finished gzip tarball, then re-executes every
Android patch in host order against those exact installed bytes. This detects
source-vs-packaged mismatches and missing modules before the APK is uploaded.
"""
import argparse
import importlib.util
import json
import os
import posixpath
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'usr/local/lib/node_modules/@deepseek-ai/dsh'
ASSETS = ROOT / 'app/src/main/assets'

def required_modules():
    registry = json.loads((ASSETS/'runtime-patches.json').read_text())
    required = {
        '@deepseek-ai/dsh/package.json',
        '@deepseek-ai/dsh/lib/bin.js',
        '@deepseek-ai/dsh-client-ui-settings/lib/client.js',
        '@deepseek-ai/dsh-client-modules/lib/index.js',
        '@deepseek-ai/dsh-web-frontend/dist/index.html',
    }
    for item in registry['active']:
        spec = json.loads((ASSETS/item['asset']).read_text())
        required.add(item.get('module') or spec['module'])
    for extra in ['pdf-compat-patch.json','workspace-directory-policy-patch.json']:
        spec=json.loads((ASSETS/extra).read_text())
        required.add(spec['module'])
        if 'resourceModule' in spec: required.add(spec['resourceModule'])
    return required

def archive_filename(relative):
    if relative == '@deepseek-ai/dsh' or relative.startswith('@deepseek-ai/dsh/'):
        return PREFIX + relative[len('@deepseek-ai/dsh'):]
    return PREFIX+'/node_modules/'+relative

def stage(archive, target):
    expected=required_modules()
    locations={archive_filename(name):name for name in expected}
    found=set()
    total=0
    file_count=0
    # Stream mode bounds memory, even for 100+ MiB gzip archives.
    with tarfile.open(archive,mode='r|gz') as tar:
        for member in tar:
            total+=1
            name=member.name
            norm=posixpath.normpath(name)
            if not name or norm!=name or name.startswith('/') or name.startswith('../'):
                raise ValueError('UNSAFE_ARCHIVE_NAME: '+name)
            if member.issym() or member.islnk():
                dest=posixpath.normpath(posixpath.join(posixpath.dirname(name),member.linkname))
                if member.linkname.startswith('/') or dest.startswith('../') or dest=='.':
                    raise ValueError('UNSAFE_ARCHIVE_LINK: '+name)
            if name not in locations: continue
            if not member.isfile():
                raise ValueError('MODULE_NOT_REGULAR_ARCHIVE_FILE:'+name)
            if member.size>32*1024*1024:
                raise ValueError('OVERSIZE_MANAGED_MODULE:'+name)
            source=tar.extractfile(member)
            if source is None:raise ValueError('UNREADABLE_MODULE:'+name)
            content=source.read(member.size+1)
            if len(content)!=member.size:raise ValueError('INCOMPLETE_MODULE:'+name)
            p=target/locations[name]
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(content)
            found.add(locations[name])
            file_count+=1
    missing=expected-found
    if missing:raise ValueError('PACKAGED_DSH_MODULE_MISSING:'+','.join(sorted(missing)))
    print('ARCHIVE_STAGED_REQUIRED_MODULES',file_count,'/',total,'tar entries',archive.stat().st_size,'bytes')

def audit(stage_root):
    filename=ROOT/'tools/verify-runtime-installation.py'
    spec=importlib.util.spec_from_file_location('dsha_install_preflight',filename)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Re-run the same Android-patch-order checker against the exact bytes
    # written by build-dsh-runtime, rather than the pristine npm tree.
    mod.MODULES=stage_root
    checks=[
      ('all registry patch chains',mod.check_patch_registry),
      ('PDF main/worker/resources',mod.check_pdf),
      ('client combiner',mod.check_client_combos),
      ('WebView bootstrap',mod.check_browser_bootstrap),
      ('LAN Host settings RPC',mod.check_lan_settings),
      ('workspace directory',mod.check_workspace_policy),
    ]
    for name,run in checks:
        try:
            result=run()
        except Exception as error:
            raise RuntimeError('PACKAGED_RUNTIME_HOST_PATCH_FAILED: '+name+': '+str(error)) from error
        print('PACKAGED_INSTALL_PASS:',name,result)
    expected=mod.VERSION
    dsh=json.loads((stage_root/'@deepseek-ai/dsh/package.json').read_text())
    if dsh.get('version')!=expected:raise ValueError('PACKAGED_DSH_VERSION_MISMATCH')
    print('PACKAGED_INSTALL_VALIDATED',expected,'all',len(checks),'installer compatibility groups passed')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('archive',type=Path)
    args=parser.parse_args()
    if not args.archive.is_file():raise SystemExit('Dsh runtime archive does not exist')
    with tempfile.TemporaryDirectory(prefix='dsha-archive-check-') as temp:
        temporary=Path(temp)
        stage(args.archive,temporary)
        audit(temporary)
if __name__=='__main__':
    main()
