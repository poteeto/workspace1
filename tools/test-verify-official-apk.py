#!/usr/bin/env python3
"""Pure logic checks for the fail-closed local release identity gate.

The actual APK cryptographic signature is validated by Android apksigner when
tools/build-official-apks.sh runs with the user's fixed new v179+ keystore.
"""
import importlib.util
import pathlib
import re
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("verify_official_apk", ROOT / "tools/verify-official-apk.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class OfficialReleaseGateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.apk = pathlib.Path(self.temp.name) / "release.apk"
        self.apk.write_bytes(b"fixture - signed binary would be checked by apksigner")
        self.code = module.one(r"^\s*versionCode\s+(\d+)\s*$", module.GRADLE, "versionCode")
        self.name = module.one(r'^\s*versionName\s+"([^"]+)"\s*$', module.GRADLE, "versionName")
        self.badging = (
            "package: name='com.dsh.client' versionCode='{}' versionName='{}'\n"
            "sdkVersion:'30'\ntargetSdkVersion:'37'\n"
        ).format(self.code, self.name)
        self.signed = (
            "Verifies\n"
            "Verified using v1 scheme (JAR signing): true\n"
            "Verified using v2 scheme (APK Signature Scheme v2): true\n"
            "Verified using v3 scheme (APK Signature Scheme v3): true\n"
            "Signer #1 certificate SHA-256 digest: " + module.IDENTITY["certificateSha256"] + "\n"
        )

    def check(self, flavor="standard", **changes):
        badging = changes.get("badging", self.badging)
        signature = changes.get("signature", self.signed)
        with mock.patch.object(module, "run", side_effect=[badging, signature]):
            module.verify(self.apk, flavor, pathlib.Path("aapt"), pathlib.Path("apksigner"))

    def test_exact_cert_version_and_scheme_pass(self):
        self.check()
        self.check("low", badging=self.badging.replace(self.name, self.name + "low"))

    def test_standard_v3_signature_is_sufficient_on_android_11(self):
        v3_only = self.signed.replace("Verified using v1 scheme (JAR signing): true",
                                      "Verified using v1 scheme (JAR signing): false").replace(
            "Verified using v2 scheme (APK Signature Scheme v2): true",
            "Verified using v2 scheme (APK Signature Scheme v2): false")
        self.check(signature=v3_only)

    def test_low_requires_all_signature_schemes(self):
        low_badging = self.badging.replace(self.name, self.name + "low")
        for mode in ("v1", "v2", "v3"):
            damaged = self.signed.replace(
                next(line for line in self.signed.splitlines() if "Verified using " + mode + " scheme" in line),
                next(line for line in self.signed.splitlines() if "Verified using " + mode + " scheme" in line).replace(": true", ": false"))
            with self.subTest(scheme=mode), self.assertRaisesRegex(ValueError, "MISSING_REQUIRED"):
                self.check("low",badging=low_badging,signature=damaged)

    def test_wrong_signer_rejected(self):
        bad = self.signed.replace(module.IDENTITY["certificateSha256"], "f" * 64)
        with self.assertRaisesRegex(ValueError, "CERTIFICATE"):
            self.check(signature=bad)

    def test_wrong_package_and_version_rejected(self):
        for wrong in (
            self.badging.replace("com.dsh.client", "com.other"),
            self.badging.replace("versionCode='{}'".format(self.code), "versionCode='99999'"),
            self.badging.replace(self.name, "something-else"),
        ):
            with self.subTest(badging=wrong), self.assertRaisesRegex(ValueError, "MISMATCH"):
                self.check(badging=wrong)

    def test_debuggable_build_rejected(self):
        with self.assertRaisesRegex(ValueError, "DEBUGGABLE"):
            self.check(badging=self.badging + "application-debuggable\n")

    def test_missing_signature_scheme_rejected(self):
        with self.assertRaisesRegex(ValueError, "MISSING_REQUIRED_V3"):
            self.check(signature=self.signed.replace(
                "Verified using v3 scheme (APK Signature Scheme v3): true",
                "Verified using v3 scheme (APK Signature Scheme v3): false"))

    def test_more_than_one_signer_rejected(self):
        with self.assertRaisesRegex(ValueError, "SIGNER_COUNT"):
            self.check(signature=self.signed + "Signer #2 certificate SHA-256 digest: " + "a" * 64 + "\n")


if __name__ == "__main__":
    unittest.main()
