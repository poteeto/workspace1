#!/usr/bin/env bash
# Android x86_64 KVM with Google native bridge for ARM-only APK.
# ABI translation must be confirmed; this is Android, but NOT native ARM64.
set -Eeuo pipefail
mkdir -p emulator-evidence
ADB="$ANDROID_HOME/platform-tools/adb"
EMULATOR="$ANDROID_HOME/emulator/emulator"
bounded() {
 local sec="$1"; shift
 python3 -c 'import subprocess,sys
try: sys.exit(subprocess.run(sys.argv[2:],timeout=float(sys.argv[1])).returncode)
except subprocess.TimeoutExpired: print("ANDROID_ADB_TIMEOUT",sys.argv[2:],flush=True);sys.exit(124)' "$sec" "$@"
}
"$EMULATOR" -avd dsha-kvm -no-window -no-audio -no-boot-anim -gpu swiftshader_indirect -memory 3072 -no-snapshot -wipe-data -accel on >emulator-evidence/emulator.log 2>&1 &
emu=$!
cleanup(){
 bounded 12 "$ADB" logcat -d -v threadtime -t 3500 >emulator-evidence/logcat.txt 2>&1 || true
 bounded 12 "$ADB" emu kill >/dev/null 2>&1 || true
 kill "$emu" >/dev/null 2>&1 || true
}
trap cleanup EXIT
online=0
for _ in $(seq 1 100); do
 if ! kill -0 "$emu" 2>/dev/null; then echo "EMULATOR_EXIT";tail -70 emulator-evidence/emulator.log;exit 1;fi
 if [[ "$(bounded 4 "$ADB" get-state 2>/dev/null || true)" == device ]];then online=1;break;fi
 sleep 2
done
test "$online" = 1 || { echo "NO_ADB";tail -80 emulator-evidence/emulator.log;exit 1; }
ready=0
for _ in $(seq 1 80);do
 if [[ "$(bounded 4 "$ADB" shell getprop sys.boot_completed | tr -d '\r')" == 1 ]];then ready=1;break;fi
 sleep 2
done
test "$ready" = 1 || { echo "ANDROID_BOOT_TIMEOUT";exit 1; }
bounded 10 "$ADB" shell input keyevent KEYCODE_WAKEUP
bounded 10 "$ADB" shell wm dismiss-keyguard
"$ADB" shell getprop ro.product.cpu.abilist | tee emulator-evidence/abi.txt
"$ADB" shell getprop ro.dalvik.vm.native.bridge | tee emulator-evidence/native-bridge.txt
echo "BRIDGE_INFO native_arm64_abi=$(cat emulator-evidence/abi.txt)"
if ! grep -q arm64-v8a emulator-evidence/abi.txt; then
 echo "ARM64_TRANSLATION_NOT_EXPOSED_IN_ANDROID_SYSTEM_IMAGE"
 exit 1
fi
main=$(find "$1" -name '*.apk' -type f -print -quit)
testapk=$(find "$2" -name '*.apk' -type f -print -quit)
test -f "$main" && test -f "$testapk"
bounded 220 "$ADB" install -r "$main" | tee emulator-evidence/install-main.txt
bounded 75 "$ADB" install -r "$testapk" | tee emulator-evidence/install-test.txt
set +e
bounded 100 "$ADB" shell am instrument -w -r com.dsh.client.test/com.deepseekharness.app.runtime.OwnedBirthAndroidInstrumentation >emulator-evidence/native-test.txt 2>&1
status=$?
set -e
cat emulator-evidence/native-test.txt
if [ "$status" -ne 0 ] || ! grep -q 'ANDROID_NATIVE_BIRTH_AND_ECHILD_PASS' emulator-evidence/native-test.txt;then
 echo "ANDROID_ARM_BRIDGE_KERNEL_SESSION_NOT_CONFIRMED";exit 1
fi
echo "ANDROID_KERNEL_NATIVE_BRIDGE_OWNED_SESSION_PASS"

# Real app process deaths, without rebooting Android. Preserve a legacy unknown record throughout.
for cycle in 1 2 3; do
 bounded 10 "$ADB" shell run-as com.dsh.client rm -f files/restart-fixture-ready
 bounded 20 "$ADB" shell am start -W -n com.dsh.client/com.deepseekharness.app.runtime.OrdinaryRestartFixtureActivity >"emulator-evidence/reopen-$cycle-start.txt"
 fixture=0
 for _ in $(seq 1 30); do
  if bounded 4 "$ADB" shell run-as com.dsh.client cat files/restart-fixture-ready 2>/dev/null | grep -q '^READY ';then fixture=1;break;fi
  sleep 1
 done
 test "$fixture" = 1 || { echo "ORDINARY_RESTART_FIXTURE_NOT_READY";exit 1; }
 if [ "$cycle" = 2 ];then
  bounded 10 "$ADB" shell input keyevent KEYCODE_HOME
  bounded 10 "$ADB" shell am kill com.dsh.client
 else
  bounded 10 "$ADB" shell am force-stop com.dsh.client
 fi
 bounded 100 "$ADB" shell am instrument -w -r -e restart_verify true com.dsh.client.test/com.deepseekharness.app.runtime.OwnedBirthAndroidInstrumentation >"emulator-evidence/reopen-$cycle-verify.txt" 2>&1
 cat "emulator-evidence/reopen-$cycle-verify.txt"
 grep -q 'ANDROID_ORDINARY_REOPEN_WITH_OLD_RECORD_PASS' "emulator-evidence/reopen-$cycle-verify.txt" || { echo "ORDINARY_APP_REOPEN_FAILED";exit 1; }
done
echo "ANDROID_THREE_APP_REOPEN_CYCLES_WITHOUT_REBOOT_PASS"

# Current UI behavior: real Android system PiP plus the production log page.
bounded 100 "$ADB" shell am instrument -w -r com.dsh.client/com.deepseekharness.app.ui.LaunchLogAudit >emulator-evidence/launch-preferences.txt 2>&1
cat emulator-evidence/launch-preferences.txt
grep -q 'ANDROID_AUTO_PIP_OPT_IN_AND_SEPARATE_LOG_PAGE_PASS' emulator-evidence/launch-preferences.txt || { echo "LAUNCH_PREFERENCES_FAILED";exit 1; }
for language in zh en; do
 bounded 240 "$ADB" shell am instrument -w -r -e mode style -e layout_only true -e language "$language" -e scenes launch_idle,launch_error,fragment_config,activity_startup_log com.dsh.client/com.deepseekharness.app.ui.LayoutAuditInstrumentation >"emulator-evidence/layout-$language.txt" 2>&1
 cat "emulator-evidence/layout-$language.txt"
 grep -q 'result=PASS' "emulator-evidence/layout-$language.txt" || { echo "NATIVE_LAYOUT_FAILED_$language";exit 1; }
 "$ADB" exec-out run-as com.dsh.client tar -C cache -cf - layout-audit >"emulator-evidence/layout-$language.tar"
done
