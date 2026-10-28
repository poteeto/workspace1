#!/usr/bin/env bash
# Smoke current published APK on a *real Android* ARM64 emulator (not Linux glibc).
# This is a fresh installation and cannot replace users' upgraded app-data tests.
set -Eeuo pipefail
mkdir -p emulator-evidence
ADB="$ANDROID_HOME/platform-tools/adb"
EMULATOR="$ANDROID_HOME/emulator/emulator"
"$EMULATOR" -avd dsha-arm64 -no-window -no-audio -no-boot-anim -gpu swiftshader -memory 2048 -no-snapshot -wipe-data -verbose >emulator-evidence/emulator.log 2>&1 &
emulator_pid=$!
cleanup(){
  "$ADB" logcat -d -v threadtime -t 3500 >emulator-evidence/logcat.txt 2>&1 || true
  "$ADB" shell dumpsys activity activities >emulator-evidence/activities.txt 2>&1 || true
  "$ADB" shell dumpsys package com.dsh.client >emulator-evidence/package.txt 2>&1 || true
  "$ADB" emu kill >/dev/null 2>&1 || true
  kill "$emulator_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT
# adb wait-for-device can block forever if an ARM hypervisor fails at boot.
device=0
for _ in $(seq 1 120); do
  if ! kill -0 "$emulator_pid" 2>/dev/null; then
    echo "ANDROID_EMULATOR_PROCESS_EXITED_BEFORE_DEVICE"
    tail -120 emulator-evidence/emulator.log || true
    exit 1
  fi
  state=$("$ADB" get-state 2>/dev/null || true)
  if [[ "$state" == device ]]; then device=1; break; fi
  sleep 2
done
if [[ "$device" != 1 ]]; then
  echo "ANDROID_EMULATOR_ADB_DEVICE_NOT_READY"
  tail -120 emulator-evidence/emulator.log || true
  exit 1
fi
ready=0
for _ in $(seq 1 160); do
  boot=$("$ADB" shell getprop sys.boot_completed | tr -d '\r')
  if [[ "$boot" == 1 ]]; then ready=1; break; fi
  sleep 2
done
test "$ready" = 1 || { echo "ANDROID_ARM64_EMULATOR_BOOT_FAILED"; exit 1; }
test "$("$ADB" shell getprop ro.product.cpu.abi | tr -d '\r')" = arm64-v8a || { echo "WRONG_ABI"; exit 1; }
printf 'DEVICE_BOOTED model=%s abi=%s sdk=%s\n' "$("$ADB" shell getprop ro.product.model)" "$("$ADB" shell getprop ro.product.cpu.abi)" "$("$ADB" shell getprop ro.build.version.sdk)"
apk=$(find "$1" -name '*.apk' -type f -print -quit)
test -n "$apk" || { echo "APK_NOT_FOUND"; exit 1; }
"$ADB" install -r "$apk"
"$ADB" shell am start -W -n com.dsh.client/com.deepseekharness.app.ui.MainActivity | tee emulator-evidence/am-start.txt
sleep 16
"$ADB" shell uiautomator dump /sdcard/window.xml >emulator-evidence/window-command.txt 2>&1 || true
"$ADB" pull /sdcard/window.xml emulator-evidence/window.xml >/dev/null 2>&1 || true
"$ADB" exec-out screencap -p >emulator-evidence/screen.png || true
"$ADB" logcat -d -v threadtime -t 3500 >emulator-evidence/logcat.txt 2>&1 || true
python3 - <<'PY'
from pathlib import Path
import re
data=Path("emulator-evidence/logcat.txt").read_text(errors="replace")
crashes=[line for line in data.splitlines() if 'FATAL EXCEPTION' in line or 'Process: com.dsh.client' in line or 'RUNTIME_CAPABILITY_UNCONFIRMED' in line or 'PROCESS_BIRTH_RECHECK_UNCONFIRMED' in line]
for line in crashes[:35]:print('ANDROID_RUNTIME_DIAGNOSTIC',line[:420])
if any('FATAL EXCEPTION' in x for x in crashes):raise SystemExit('DSHA_PROCESS_CRASHED_ON_ANDROID')
print('ANDROID_ARM64_APK_INSTALLED_AND_ACTIVITY_LAUNCHED')
PY
