#!/usr/bin/env bash
# Local-only formal signing. Never uploads keys or APKs to GitHub.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

: "${DSHA_KEYSTORE:?Historical E7E3 signing keystore is required; cannot release Debug APK}"
: "${DSHA_KEYSTORE_PASSWORD:?Missing signing keystore password}"
: "${DSHA_KEY_PASSWORD:?Missing signing key password}"
if [[ ! -f "$DSHA_KEYSTORE" ]]; then
  echo "Historical signing key not present; refusing official release." >&2
  exit 1
fi
if [[ -z "${ANDROID_HOME:-}" && -z "${ANDROID_SDK_ROOT:-}" ]]; then
  echo "ANDROID_HOME or ANDROID_SDK_ROOT is required." >&2
  exit 1
fi
sdk="${ANDROID_HOME:-$ANDROID_SDK_ROOT}"
buildtools="$(python3 tools/ci-toolchain.py --field buildTools)"
aapt="$sdk/build-tools/$buildtools/aapt"
apksigner="$sdk/build-tools/$buildtools/apksigner"
for tool in "$aapt" "$apksigner"; do
  [[ -x "$tool" ]] || { echo "Missing Android SDK release verifier: $tool" >&2; exit 1; }
done
flavor="${1:-standard}"
case "$flavor" in
  standard) gradleTask="assembleStandardRelease"; apk="app/build/outputs/apk/standard/release/app-standard-release.apk"; outfile="dsha-0.2.1-rc2.1.apk" ;;
  low) gradleTask="assembleLowRelease"; apk="app/build/outputs/apk/low/release/app-low-release.apk"; outfile="dsha-0.2.1-rc2.1low.apk" ;;
  *) echo "Specify standard or low." >&2; exit 1 ;;
esac
# Gradle refuses releases without the historical signing key, and checks
# that its certificate equals ci/release-identity.json BEFORE packing.
chmod +x gradlew
./gradlew ":app:$gradleTask" --no-daemon --max-workers=2
python3 tools/verify-official-apk.py \
  --apk "$apk" --flavor "$flavor" --aapt "$aapt" --apksigner "$apksigner"
python3 tools/verify-apk-runtime-contract.py "$apk"
dest="${DSHA_RELEASE_DIR:-release/0.2.1-rc2.1}"
mkdir -p "$dest"
# Write only after all checks pass; never overwrite existing release bytes.
if [[ -e "$dest/$outfile" || -e "$dest/$outfile.sha256" ]]; then
  echo "An existing release asset would be overwritten. Stop and review it." >&2
  exit 1
fi
cp -- "$apk" "$dest/$outfile"
(cd "$dest" && sha256sum "$outfile" > "$outfile.sha256")
echo "LOCALLY_VERIFIED_E7E3_RELEASE $dest/$outfile"
