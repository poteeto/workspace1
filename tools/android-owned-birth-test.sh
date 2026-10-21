#!/usr/bin/env bash
# Actual Android/Bionic ARM64 kernel peer ownership test.
# This is a disposable emulator; never touches a user's device or app data.
set -Eeuo pipefail
mkdir -p emulator-evidence
ADB="$ANDROID_HOME/platform-tools/adb"
EMULATOR="$ANDROID_HOME/emulator/emulator"
bounded() {
  local seconds="$1"; shift
  python3 -c 'import subprocess,sys
try: sys.exit(subprocess.run(sys.argv[2:],timeout=float(sys.argv[1])).returncode)
except subprocess.TimeoutExpired:
 print("ANDROID_ADB_COMMAND_TIMEOUT",sys.argv[2:],flush=True)
 sys.exit(124)' "$seconds" "$@"
}
"$EMULATOR" -avd dsha-arm64 -no-window -no-audio -no-boot-anim -gpu swiftshader -memory 2048 -no-snapshot -wipe-data >emulator-evidence/emulator.log 2>&1 &
emulator_pid=$!
cleanup() {
  bounded 20 "$ADB" logcat -d -v threadtime -t 5500 >emulator-evidence/logcat.txt 2>&1 || true
  bounded 20 "$ADB" shell dumpsys activity activities >emulator-evidence/activities.txt 2>&1 || true
  bounded 20 "$ADB" shell dumpsys package com.dsh.client >emulator-evidence/package.txt 2>&1 || true
  bounded 12 "$ADB" emu kill >/dev/null 2>&1 || true
  kill "$emulator_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

online=0
for _ in $(seq 1 120); do
  if ! kill -0 "$emulator_pid" 2>/dev/null; then
    echo "ANDROID_EMULATOR_EXIT_BEFORE_BOOT"; tail -100 emulator-evidence/emulator.log
    exit 1
  fi
  if [[ "$(bounded 6 "$ADB" get-state 2>/dev/null || true)" == device ]]; then online=1; break; fi
  sleep 2
done
if [[ "$online" != 1 ]]; then
  echo "ANDROID_EMULATOR_NO_ADB_AFTER_240S"; tail -100 emulator-evidence/emulator.log
  exit 1
fi
ready=0
for _ in $(seq 1 100); do
  if [[ "$(bounded 6 "$ADB" shell getprop sys.boot_completed | tr -d '\r')" == 1 ]]; then ready=1; break; fi
  sleep 2
done
if [[ "$ready" != 1 ]]; then
  echo "ANDROID_EMULATOR_BOOT_TIMEOUT"; tail -100 emulator-evidence/emulator.log
  exit 1
fi
abi=$(bounded 6 "$ADB" shell getprop ro.product.cpu.abi | tr -d '\r')
[[ "$abi" == arm64-v8a ]] || { echo "EMULATOR_WRONG_ABI:$abi"; exit 1; }
echo "ANDROID_ARM64_DEVICE_STARTED $abi"
app=$(find "$1" -type f -name '*.apk' -print -quit)
fixture=$(find "$2" -type f -name '*.apk' -print -quit)
[[ -f "$app" && -f "$fixture" ]] || { echo "MISSING_MAIN_OR_INSTRUMENTATION_APK"; exit 1; }
bounded 240 "$ADB" install -r "$app"
bounded 60 "$ADB" install -r "$fixture"
set +e
bounded 90 "$ADB" shell am instrument -w -r \
  com.dsh.client.test/com.deepseekharness.app.runtime.OwnedBirthAndroidInstrumentation \
  >emulator-evidence/owned-birth-instrumentation.txt 2>&1
instrument_status=$?
set -e
cat emulator-evidence/owned-birth-instrumentation.txt
if [[ "$instrument_status" -ne 0 ]] ||
   ! grep -q 'ANDROID_NATIVE_BIRTH_AND_ECHILD_PASS' emulator-evidence/owned-birth-instrumentation.txt; then
  echo "ANDROID_NATIVE_BIRTH_TEST_FAILED"
  exit 1
fi
echo "ANDROID_NATIVE_BIRTH_TEST_PASSED"
bounded 25 "$ADB" shell am start -W -n com.dsh.client/com.deepseekharness.app.ui.MainActivity \
  >emulator-evidence/main-activity-start.txt 2>&1 || true
sleep 8
bounded 20 "$ADB" exec-out screencap -p >emulator-evidence/screen.png || true
bounded 45 "$ADB" shell uiautomator dump /sdcard/dsha-window.xml >emulator-evidence/ui-dump.txt 2>&1 || true
bounded 20 "$ADB" pull /sdcard/dsha-window.xml emulator-evidence/window.xml >/dev/null 2>&1 || true
bounded 20 "$ADB" logcat -d -v threadtime -t 5500 >emulator-evidence/logcat.txt || true
python3 - <<'PY'
from pathlib import Path
text=Path("emulator-evidence/logcat.txt").read_text(errors="replace")
errors=[s for s in text.splitlines() if
  'FATAL EXCEPTION' in s or
  'PROCESS_BIRTH_RECHECK_UNCONFIRMED' in s or
  'DSHA_ANDROID_BIRTH_TEST' in s]
for line in errors[:30]:print('ANDROID_REAL_KERNEL_LOG',line[-400:])
if any('FATAL EXCEPTION' in line for line in errors):
    raise SystemExit('ANDROID_APP_FATAL_EXCEPTION')
print('ANDROID_EMULATOR_INSTRUMENTED_NATIVE_PROCESS_AND_ACTIVITY_PASS')
PY
