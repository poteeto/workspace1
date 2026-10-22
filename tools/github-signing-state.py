#!/usr/bin/env python3
"""Validate or initialize the single GitHub publishing identity; never rotate implicitly."""
import json
import pathlib
import re
import sys


def mode(root):
    root = pathlib.Path(root)
    identity = json.loads((root / 'ci/release-identity.json').read_text(encoding='utf-8'))
    if identity.get('schema') != 1 or identity.get('packageName') != 'com.dsh.client':
        raise ValueError('SIGNING_IDENTITY_SCHEMA')
    if not re.fullmatch('[a-f0-9]{64}', identity.get('certificateSha256', '')):
        raise ValueError('SIGNING_IDENTITY_CERTIFICATE')
    cipher = root / 'ci/github-signing/dsha-permanent-release.p12.gpg'
    marker = root / 'ci/github-signing/certificate.sha256'
    state = identity.get('githubSigningState')
    if state == 'bootstrap-authorized' and not cipher.exists() and not marker.exists():
        return 'bootstrap'
    if state != 'active' or not cipher.is_file() or not marker.is_file() or not cipher.stat().st_size:
        raise ValueError('SIGNING_ESCROW_INCOMPLETE_REFUSING_KEY_ROTATION')
    if marker.read_text(encoding='ascii') != identity['certificateSha256'] + '\n':
        raise ValueError('SIGNING_ESCROW_CERTIFICATE_MISMATCH')
    return 'reuse'


def activate(root, fingerprint):
    root = pathlib.Path(root)
    if mode(root) != 'bootstrap' or not re.fullmatch('[a-f0-9]{64}', fingerprint):
        raise ValueError('SIGNING_BOOTSTRAP_NOT_AUTHORIZED')
    path = root / 'ci/release-identity.json'
    identity = json.loads(path.read_text(encoding='utf-8'))
    identity.update(certificateSha256=fingerprint, githubSigningState='active')
    path.write_text(json.dumps(identity, indent=2) + '\n', encoding='utf-8')
    marker = root / 'ci/github-signing/certificate.sha256'
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(fingerprint + '\n', encoding='ascii')


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'activate':
        activate(pathlib.Path(__file__).resolve().parents[1], sys.argv[2])
    else:
        print(mode(pathlib.Path(__file__).resolve().parents[1]))
