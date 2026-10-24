#!/usr/bin/env python3
"""固定 Ubuntu glibc 搜索工具；不执行安装脚本，不改 Ubuntu base 或 npm 包。"""
import argparse, hashlib, lzma, os, struct, subprocess, urllib.request
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LOCK=json.loads((ROOT/'tools/android-ripgrep.lock.json').read_text())
ASSETS=ROOT/'app/src/main/assets/ripgrep'
sha=lambda data:hashlib.sha256(data).hexdigest()

def validate_elf(data):
    if data[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',data,18)[0]!=183:
        raise ValueError('RIPGREP_NOT_ARM64_ELF')
    offset=struct.unpack_from('<Q',data,32)[0]
    size,count=struct.unpack_from('<HH',data,54)
    interpreters=[]
    for i in range(count):
        at=offset+i*size
        if struct.unpack_from('<I',data,at)[0]==3:
            begin=struct.unpack_from('<Q',data,at+8)[0];length=struct.unpack_from('<Q',data,at+32)[0]
            interpreters.append(data[begin:begin+length])
    if interpreters!=[b'/lib/ld-linux-aarch64.so.1\x00']:raise ValueError('RIPGREP_REQUIRES_GLIBC_DYNAMIC_ELF')

def check():
    binary=(ASSETS/'rg.bin').read_bytes();validate_elf(binary)
    if sha(binary)!=LOCK['binarySha256'] or sha((ASSETS/'copyright').read_bytes())!=LOCK['copyrightSha256']:
        raise ValueError('ANDROID_RIPGREP_ASSET_HASH')
    print('PASS pinned ARM64 glibc ripgrep and copyright')

def prepare(cache):
    cache.mkdir(parents=True,exist_ok=True)
    def fetch(relative,expected):
        target=cache/Path(relative).name
        if not target.is_file() or sha(target.read_bytes())!=expected:
            with urllib.request.urlopen(LOCK['source']+relative,timeout=60) as response:data=response.read()
            if sha(data)!=expected:raise ValueError('RIPGREP_DOWNLOAD_HASH:'+relative)
            target.write_bytes(data)
        return target
    release=fetch(LOCK['inRelease'],LOCK['inReleaseSha256'])
    # Ubuntu 的固定签名索引与项目既有 noble 基础工具使用同一 InRelease。
    if os.name!='nt':subprocess.run(['gpgv','--keyring','/usr/share/keyrings/ubuntu-archive-keyring.gpg',str(release)],check=True)
    index=fetch(LOCK['index'],LOCK['indexSha256'])
    if not any(LOCK['indexSha256'] in line and 'universe/binary-arm64/Packages.xz' in line for line in release.read_text().splitlines()):raise ValueError('RIPGREP_INDEX_NOT_IN_RELEASE')
    paragraphs=lzma.decompress(index.read_bytes()).decode().split('\n\n')
    row=next(p for p in paragraphs if p.startswith('Package: ripgrep\n'))
    fields=dict(line.split(': ',1) for line in row.splitlines() if ': ' in line and not line.startswith(' '))
    for name,value in [('Architecture','arm64'),('Version',LOCK['version']),('Filename',LOCK['filename']),('SHA256',LOCK['sha256']),('Size',str(LOCK['size']))]:
        if fields.get(name)!=value:raise ValueError('RIPGREP_PACKAGE_INDEX:'+name)
    deb=fetch(LOCK['filename'],LOCK['sha256']).read_bytes()
    if len(deb)!=LOCK['size'] or deb[:8]!=b'!<arch>\n':raise ValueError('RIPGREP_DEB_FORMAT')
    offset=8;payload=None
    while offset<len(deb):
        header=deb[offset:offset+60];name=header[:16].decode().strip().rstrip('/');size=int(header[48:58]);data=deb[offset+60:offset+60+size];offset+=60+size+size%2
        if name=='data.tar.zst':payload=data
    if payload is None:raise ValueError('RIPGREP_DEB_PAYLOAD')
    archive=cache/'data.tar.zst';archive.write_bytes(payload);ASSETS.mkdir(parents=True,exist_ok=True)
    for member,output,expected in [('./usr/bin/rg','rg.bin',LOCK['binarySha256']),('./usr/share/doc/ripgrep/copyright','copyright',LOCK['copyrightSha256'])]:
        command=['tar',*(['--zstd'] if os.name!='nt' else []),'-xOf',str(archive),member]
        data=subprocess.check_output(command)
        if sha(data)!=expected:raise ValueError('RIPGREP_EXTRACTED_HASH:'+member)
        (ASSETS/output).write_bytes(data)
    check()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cache',type=Path,default=ROOT/'app/build/android-ripgrep-cache');parser.add_argument('--check',action='store_true');args=parser.parse_args()
    if args.check:check()
    else:prepare(args.cache)
