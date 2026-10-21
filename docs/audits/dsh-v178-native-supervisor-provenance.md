# DSHA v178 Android native supervisor protocol provenance

## Cause observed on 2026-10-22

The failed Android 15 KVM ARM translation run [39659891480](https://github.com/poteeto/workspace1/actions/runs/39659891480) installed the v177 APK and Android instrumentation successfully, but ended at `IOException: OWNED_CONTROL_ACCEPT_UNCONFIRMED`.

Examining the **actual APK artifact** from build run [39657235016](https://github.com/poteeto/workspace1/actions/runs/39657235016), its `lib/arm64-v8a/libdsha-session.so` is 7392 bytes and contains old messages `DSHA_SESSION_WAIT`, `DSHA_SESSION_PARENT` and `DSHA_SESSION_FORK`; it does **not** contain `READY DSHA_OWNED_TREE_V2`, `OWNED_TREE_EMPTY ECHILD` or `NO_GUEST`. The current `tools/native-session/session-launcher.c` and `NativeTreeControl.java` require those V2 messages. Thus Java/native APK protocol divergence, not merely socket scheduling latency, is confirmed. This does not by itself rule out additional device problems.

## v178 preventive fix

- Build the Android/Bionic ARM64 supervisor from this commit's `tools/native-session/session-launcher.c` using the pinned NDK via `tools/native-session/build.py`.
- Immediately recompile and byte-compare with `--check`; require the exact V2 control protocol strings.
- After Gradle assembly compare every byte of the APK's `libdsha-session.so` with the newly compiled ELF and verify the V2 markers in the **shipped APK**.
- Tie the Android 15 emulator test job to the APK and instrumentation artifacts of the **same CI run** via `needs: test-apk`. Historical workflow `android-v177-kvm-bridge.yml` remains forensic only; it downloads a fixed obsolete build and cannot certify v178.
- Retain PID, owner UID, birth, SO_PEERCRED, ECHILD and no-guest proof requirements; never accept a host or emulator result as phone/OEM acceptance.

## Remaining acceptance criteria

1. v178 debug APK and instrumentation must compile and pass the V2 provenance gate.
2. Android 15 native-bridge emulator must actually report `ANDROID_NATIVE_BIRTH_AND_ECHILD_PASS`, not just install success.
3. Full cold BXROOT setup, OEM SELinux/procfs and existing-session migration still require separately collected device evidence.
4. Never uninstall/wipe user data, change E7E3 signing identity, automatically merge the draft PR, or publish an unverified release.
