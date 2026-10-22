#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import tempfile
import unittest
spec = importlib.util.spec_from_file_location('signing_state', pathlib.Path(__file__).with_name('github-signing-state.py'))
state = importlib.util.module_from_spec(spec)
spec.loader.exec_module(state)

class SigningStateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        (self.root/'ci/github-signing').mkdir(parents=True)
        self.identity = self.root/'ci/release-identity.json'
        self.cipher = self.root/'ci/github-signing/dsha-permanent-release.p12.gpg'
        self.marker = self.root/'ci/github-signing/certificate.sha256'
        self.identity.write_text(json.dumps({'schema':1,'packageName':'com.dsh.client','certificateSha256':'a'*64,'githubSigningState':'bootstrap-authorized'}))
    def activate(self):
        state.activate(self.root, 'b'*64)
        self.cipher.write_bytes(b'encrypted fixture')
    def test_one_time_activation_and_reuse(self):
        self.assertEqual('bootstrap', state.mode(self.root))
        self.activate()
        self.assertEqual('reuse', state.mode(self.root))
        with self.assertRaises(ValueError): state.activate(self.root, 'c'*64)
        self.assertEqual('b'*64+'\n', self.marker.read_text())
    def test_lost_cipher_marker_or_both_never_rotates(self):
        for missing in ['cipher','marker','both']:
            with self.subTest(missing=missing):
                if self.marker.exists(): self.marker.unlink()
                if self.cipher.exists(): self.cipher.unlink()
                data=json.loads(self.identity.read_text()); data['githubSigningState']='bootstrap-authorized'; self.identity.write_text(json.dumps(data))
                self.activate()
                if missing in ['cipher','both']: self.cipher.unlink()
                if missing in ['marker','both']: self.marker.unlink()
                with self.assertRaisesRegex(ValueError,'INCOMPLETE'): state.mode(self.root)
    def test_partial_bootstrap_or_empty_cipher_is_rejected(self):
        self.marker.write_text('b'*64+'\n')
        with self.assertRaises(ValueError): state.mode(self.root)
        self.marker.unlink(); self.activate(); self.cipher.write_bytes(b'')
        with self.assertRaises(ValueError): state.mode(self.root)
    def test_mismatching_certificate_is_rejected(self):
        self.activate(); self.marker.write_text('c'*64+'\n')
        with self.assertRaisesRegex(ValueError,'MISMATCH'): state.mode(self.root)
    def test_missing_bootstrap_authorization_is_rejected(self):
        data=json.loads(self.identity.read_text()); del data['githubSigningState']; self.identity.write_text(json.dumps(data))
        with self.assertRaises(ValueError): state.mode(self.root)
    def test_wrong_package_is_rejected(self):
        data=json.loads(self.identity.read_text()); data['packageName']='other.app'; self.identity.write_text(json.dumps(data))
        with self.assertRaises(ValueError): state.mode(self.root)

if __name__ == '__main__': unittest.main()
