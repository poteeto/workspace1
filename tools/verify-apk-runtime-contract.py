#!/usr/bin/env python3
"""Byte-level APK release gate for every signed managed-runtime input.

The source-side descriptor and generated asset receipt must match the *actual*
compressed contents of the APK, not merely code in the CI workspace.
All packaged assets are read by bounded streaming; user data is never touched.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'app/src/main/assets'

def sha_stream(stream):
    digest=hashlib.sha256()
    for part in iter(lambda: stream.read(1024*1024),b''):
        digest.update(part)
    return digest.hexdigest()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('apk',type=Path)
    args=parser.parse_args()
    if not args.apk.is_file():raise SystemExit('APK_NOT_FOUND')
    source=json.loads((ASSETS/'runtime-descriptor.json').read_text(encoding='utf8'))
    with zipfile.ZipFile(args.apk) as apk:
        names=apk.namelist()
        if len(names)!=len(set(names)):raise SystemExit('APK_DUPLICATE_ZIP_ENTRY')
        embedded=json.loads(apk.read('assets/runtime-descriptor.json'))
        if embedded!=source:raise SystemExit('APK_DESCRIPTOR_NOT_SAME_AS_VERIFIED_SOURCE')
        receipts=embedded.get('inputs')
        if not isinstance(receipts,dict) or len(receipts)<250:
            raise SystemExit('APK_RUNTIME_INPUT_RECEIPT_TOO_SMALL')
        manifest=json.loads(apk.read('assets/managed-runtime-inputs.json'))
        if manifest.get('schema')!=1:raise SystemExit('APK_MANAGED_INPUT_SCHEMA')
        installed={e['asset'] for e in manifest['installs']}
        if not installed.issubset(receipts):raise SystemExit('APK_INSTALL_ASSETS_NOT_IN_DESCRIPTOR')
        for name,want in sorted(receipts.items()):
            if name.startswith('/') or '..' in Path(name).parts or '\\' in name:
                raise SystemExit('APK_UNSAFE_RECEIPT_NAME:'+name)
            member='assets/'+name
            if member not in names:raise SystemExit('APK_MANAGED_ASSET_MISSING:'+name)
            if not isinstance(want,str) or len(want)!=64:raise SystemExit('APK_INVALID_MANAGED_HASH:'+name)
            with apk.open(member) as stream:
                actual=sha_stream(stream)
            if want!=actual:raise SystemExit('APK_MANAGED_ASSET_BYTE_MISMATCH:'+name)
        mandatory=('dsh-runtime.bin','offline-rootfs.bin','ubuntu-tools.bin')
        if any(x not in receipts for x in mandatory):
            raise SystemExit('APK_LINUX_DSH_ASSET_NOT_CHECKSUM_PINNED')
        print('APK_BYTE_CONTRACT_PASS',len(receipts),'files',len(installed),
              'managed installer targets, runtimeId',embedded['runtimeId'],
              'dshVersion',embedded['dshVersion'])
if __name__=='__main__':
    main()
