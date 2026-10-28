#!/usr/bin/env python3
import importlib.util
import pathlib
import tempfile
import unittest
import zipfile
spec=importlib.util.spec_from_file_location('gate',pathlib.Path(__file__).with_name('verify-signed-apk-content.py'))
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
class SignedContentTest(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.a=pathlib.Path(self.temp.name)/'a.apk';self.b=self.a.with_name('b.apk')
  self.base={'AndroidManifest.xml':b'manifest','classes.dex':b'code','resources.arsc':b'resources','assets/runtime-descriptor.json':b'descriptor','META-INF/services/provider':b'service'}
  self.write(self.a,self.base)
 def write(self,path,entries):
  with zipfile.ZipFile(path,'w') as z:
   for n,c in entries.items():z.writestr(n,c)
 def test_signature_metadata_is_allowed(self):
  self.write(self.b,{**self.base,'META-INF/DSHA-PUB.RSA':b'cert','META-INF/DSHA-PUB.SF':b'signature','META-INF/MANIFEST.MF':b'digests'})
  gate.verify(self.a,self.b)
 def test_every_original_entry_is_checked(self):
  for name in self.base:
   with self.subTest(name=name):
    changed=dict(self.base);changed[name]+=b'changed';self.write(self.b,changed)
    with self.assertRaisesRegex(ValueError,'CONTENT_DRIFT'):gate.verify(self.a,self.b)
 def test_added_application_bytes_are_rejected(self):
  self.write(self.b,{**self.base,'assets/unexpected':b'extra'})
  with self.assertRaisesRegex(ValueError,'MEMBER_DRIFT'):gate.verify(self.a,self.b)
 def test_removed_application_bytes_are_rejected(self):
  changed=dict(self.base);del changed['classes.dex'];self.write(self.b,changed)
  with self.assertRaisesRegex(ValueError,'MEMBER_DRIFT'):gate.verify(self.a,self.b)
 def test_duplicate_entries_are_rejected(self):
  self.write(self.b,self.base)
  with zipfile.ZipFile(self.b,'a') as z:z.writestr('classes.dex',b'other')
  with self.assertRaisesRegex(ValueError,'DUPLICATE'):gate.verify(self.a,self.b)
if __name__=='__main__':unittest.main()
