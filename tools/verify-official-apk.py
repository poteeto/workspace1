#!/usr/bin/env python3
"""Fail-closed checks for a locally signed, release-mode DSHA APK.

This does not create signatures. apksigner must validate the actual APK and
the signer must equal the historical, in-place-upgrade-compatible certificate.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = json.loads((ROOT / "ci/release-identity.json").read_text(encoding="utf-8"))
GRADLE = (ROOT / "app/build.gradle").read_text(encoding="utf-8")


def run(*args):
    result = subprocess.run(args, check=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    return result.stdout


def one(pattern, text, label):
    values = re.findall(pattern, text, flags=re.MULTILINE)
    if len(values) != 1:
        raise ValueError("RELEASE_IDENTITY_UNDETERMINED: " + label)
    return values[0]


def verify(apk, flavor, aapt, apksigner):
    if not apk.is_file() or not apk.stat().st_size:
        raise ValueError("MISSING_RELEASE_APK")
    if IDENTITY.get("schema") != 1 or IDENTITY.get("packageName") != "com.dsh.client":
        raise ValueError("INVALID_RELEASE_IDENTITY")
    want_cert = IDENTITY["certificateSha256"].lower()
    if not re.fullmatch(r"[a-f0-9]{64}", want_cert):
        raise ValueError("INVALID_EXPECTED_CERTIFICATE")
    if flavor not in ("standard", "low"):
        raise ValueError("INVALID_RELEASE_FLAVOR")

    # Read binary AndroidManifest.xml using the Android SDK, not a source-side guess.
    badging = run(str(aapt), "dump", "badging", str(apk))
    expected_code = one(r"^\s*versionCode\s+(\d+)\s*$", GRADLE, "versionCode")
    expected_name = one(r'^\s*versionName\s+"([^"]+)"\s*$', GRADLE, "versionName")
    expected_package = IDENTITY["packageName"]
    package = one(r"^package: name='([^']+)'", badging, "package")
    version_code = one(r"^package:.*versionCode='([^']+)'", badging, "code")
    version_name = one(r"^package:.*versionName='([^']+)'", badging, "name")
    if (package, version_code, version_name) != (
        expected_package, expected_code, expected_name + ("low" if flavor == "low" else "")):
        raise ValueError("APK_PACKAGE_VERSION_OR_FLAVOR_MISMATCH")
    if "application-debuggable" in badging:
        raise ValueError("APK_IS_DEBUGGABLE")

    # apksigner returns nonzero for cryptographically invalid or malformed signatures.
    signatures = run(str(apksigner), "verify", "--verbose", "--print-certs", str(apk))
    signers = re.findall(
        r"^Signer #(\d+) certificate SHA-256 digest: ([0-9a-fA-F:]{64,95})\s*$",
        signatures, flags=re.MULTILINE)
    if len(signers) != 1 or signers[0][0] != "1":
        raise ValueError("APK_SIGNER_COUNT_INVALID")
    actual_cert = signers[0][1].replace(":", "").lower()
    if actual_cert != want_cert:
        raise ValueError("APK_PUBLISH_CERTIFICATE_NOT_HISTORICAL_E7E3")

    # The historical release identity intentionally requires all three signature schemes.
    for scheme in IDENTITY.get("schemes", []):
        scheme_name = {"v1": "v1 scheme", "v2": "v2 scheme", "v3": "v3 scheme"}.get(scheme)
        if not scheme_name:
            raise ValueError("UNKNOWN_REQUIRED_SIGNATURE_SCHEME")
        if not re.search(
            r"^Verified using " + re.escape(scheme_name) + r"\b[^\n]*:\s*true\s*$",
            signatures, flags=re.MULTILINE | re.IGNORECASE):
            raise ValueError("MISSING_REQUIRED_" + scheme.upper() + "_SIGNATURE")
    print("HISTORICAL_CERTIFICATE_VERIFIED", package, version_code, flavor, actual_cert)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", required=True, type=Path)
    parser.add_argument("--flavor", required=True, choices=["standard", "low"])
    parser.add_argument("--aapt", required=True, type=Path)
    parser.add_argument("--apksigner", required=True, type=Path)
    args = parser.parse_args()
    try:
        verify(args.apk, args.flavor, args.aapt, args.apksigner)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit("OFFICIAL_APK_GATE_FAILED: " + str(error)) from None


if __name__ == "__main__":
    main()
