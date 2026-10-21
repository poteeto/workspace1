#!/usr/bin/env python3
"""Restore missing immutable ARM64 offline inputs from checksum-verified official
DSHA 0.2.0-rc2 release APK. Never import its old DSH runtime.
Intended only for CI / local reproducible test builds, not source commits.
"""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'app/src/main/assets'
APK_SHA='1fedf883d431af658d89c28b86d85974cc1d11b74e0c5d46ef3d3cf8650b1961'
def sha(b):return hashlib.sha256(b).hexdigest()
def main(apk):
    if sha(apk.read_bytes())!=APK_SHA:raise ValueError('UNVERIFIED_UPSTREAM_APK')
    descriptor=json.loads((ASSETS/'runtime-descriptor.json').read_text())
    if descriptor.get('dshVersion')!='0.2.0-rc.2':raise ValueError('UNEXPECTED_BASELINE_DESCRIPTOR')
    required=('offline-rootfs.bin','ubuntu-tools.bin')
    with zipfile.ZipFile(apk) as archive:
        for name in required:
            raw=archive.read('assets/'+name)
            expected=descriptor['inputs'].get(name)
            if expected!=sha(raw):raise ValueError('BASELINE_ASSET_HASH:'+name)
            target=ASSETS/name
            if target.is_symlink() or target.exists() and sha(target.read_bytes())!=expected:
                raise ValueError('UNEXPECTED_ASSET_PREEXISTS:'+name)
            target.write_bytes(raw)
            print('RESTORED_VERIFIED',name,len(raw),expected)
    # The private source snapshot omits large archive metadata: recreate the
    # exact source-bound metadata from its original pinned apt package lock.
    spec=importlib.util.spec_from_file_location('dsha_ubuntu_tools',ROOT/'tools/prepare-ubuntu-tools.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    lock=json.loads((ROOT/'tools/ubuntu-tools/packages.lock.json').read_text())
    manifest=json.loads((ASSETS/'ubuntu-tools.manifest.json').read_text())
    assert (ASSETS/'ubuntu-tools.layout').read_text().strip()=='configured-overlay-v1'
    metadata={
        'inputs':module.inputs(),
        'archive_sha256':sha((ASSETS/'ubuntu-tools.bin').read_bytes()),
        'installed_bytes':sum(int(r['Installed-Size'])*1024 for r in lock['packages']),
        'base_status_sha256':lock['baseStatusSha256'],
        'packages':len(lock['packages']),
        'layout':'configured-overlay-v1',
        'status_sha256':manifest['statusSha256']
    }
    if metadata['archive_sha256']!=manifest['archiveSha256']:raise ValueError('UBUNTU_OVERLAY_MANIFEST_HASH')
    (ASSETS/'ubuntu-tools.inputs.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print('RESTORED_UBUNTU_TOOLS_METADATA',len(lock['packages']))
if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: python tools/ci-restore-upstream-base.py /path/to/official.apk')
    main(Path(sys.argv[1]))
