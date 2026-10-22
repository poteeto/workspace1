#!/usr/bin/env python3
"""Signing may change signature metadata, never application or runtime bytes."""
import hashlib
import re
import sys
import zipfile
SIGNATURE = re.compile(r'META-INF/(?:MANIFEST\.MF|[A-Za-z0-9_-]+\.(?:SF|RSA|DSA|EC))')
def content(z):
    names=z.namelist()
    if len(names)!=len(set(names)): raise ValueError('DUPLICATE_APK_ENTRY')
    return {name for name in names if not SIGNATURE.fullmatch(name)}
def digest(z,name):
    with z.open(name) as stream: return hashlib.file_digest(stream,'sha256').hexdigest()
def verify(before,after):
    with zipfile.ZipFile(before) as a,zipfile.ZipFile(after) as b:
        if content(a)!=content(b): raise ValueError('SIGNED_APK_MEMBER_DRIFT')
        for name in sorted(content(a)):
            if digest(a,name)!=digest(b,name): raise ValueError('SIGNED_APK_CONTENT_DRIFT:'+name)
    print('SIGNED_APK_ALL_APPLICATION_BYTES_VERIFIED')
if __name__=='__main__': verify(*sys.argv[1:])
