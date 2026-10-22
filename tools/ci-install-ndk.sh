#!/usr/bin/env bash
# Official r26d archive/size/checksum: https://github.com/android/ndk/wiki/Unsupported-Downloads
set -euo pipefail
cd "$(dirname "$0")/.."
ndk="$(python3 tools/ci-toolchain.py --field ndk)"
[[ "$ndk" == '26.3.11579264' ]] || { echo 'NDK_DOWNLOAD_LOCK_NOT_UPDATED' >&2; exit 1; }
target="$ANDROID_HOME/ndk/$ndk"
if [[ -f "$target/source.properties" ]] && grep -qx 'Pkg.Revision = 26.3.11579264' "$target/source.properties"; then
  test -x "$target/toolchains/llvm/prebuilt/linux-x86_64/bin/clang"
  echo 'PINNED_NDK_ALREADY_INSTALLED'; exit 0
fi
[[ ! -e "$target" ]] || { echo 'PARTIAL_NDK_INSTALL_REQUIRES_REVIEW' >&2; exit 1; }
scratch="$(mktemp -d "$RUNNER_TEMP/dsha-ndk-XXXXXXXX")"
trap 'rm -rf -- "$scratch"' EXIT
url='https://dl.google.com/android/repository/android-ndk-r26d-linux.zip'
size=668556491
chunk=167139123
pids=()
for i in 0 1 2 3; do
  begin=$((i * chunk)); end=$((begin + chunk - 1))
  if (( end >= size )); then end=$((size - 1)); fi
  length=$((end - begin + 1))
  echo "Downloading official pinned NDK part $((i+1))/4 ($length bytes)"
  (
    curl --fail --location --silent --show-error --retry 2 --retry-all-errors \
      --connect-timeout 20 --max-time 300 --speed-time 30 --speed-limit 32768 \
      --max-filesize "$length" --range "$begin-$end" "$url" -o "$scratch/part-$i"
    test "$(stat -c %s "$scratch/part-$i")" = "$length"
  ) &
  pids+=("$!")
done
failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
[[ "$failed" == 0 ]] || { echo 'PINNED_NDK_DOWNLOAD_FAILED' >&2; exit 1; }
cat "$scratch/part-0" "$scratch/part-1" "$scratch/part-2" "$scratch/part-3" > "$scratch/ndk.zip"
test "$(stat -c %s "$scratch/ndk.zip")" = "$size"
echo "fcdad75a765a46a9cf6560353f480db251d14765  $scratch/ndk.zip" | sha1sum -c -
unzip -q "$scratch/ndk.zip" -d "$scratch/unpacked"
grep -qx 'Pkg.Revision = 26.3.11579264' "$scratch/unpacked/android-ndk-r26d/source.properties"
test -x "$scratch/unpacked/android-ndk-r26d/toolchains/llvm/prebuilt/linux-x86_64/bin/clang"
mkdir -p "$ANDROID_HOME/ndk"
mv "$scratch/unpacked/android-ndk-r26d" "$target"
echo 'PINNED_OFFICIAL_NDK_VERIFIED_AND_INSTALLED'
