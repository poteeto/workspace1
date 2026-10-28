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

## v178 verified CI result (2026-10-22)

- [Build and same-run Android emulator workflow 39670697314](https://github.com/poteeto/workspace1/actions/runs/39670697314): **success**, with full Standard Debug APK assembly, standalone instrumentation assembly, and bit-for-bit proof that the shipped APK's `lib/arm64-v8a/libdsha-session.so` equals the rebuilt source binary.
- The pinned-26.3.11579264-NDK ELF is 13,816 bytes; reproducible SHA-256 `5a2a6e61f8849a4c4cbd5ecbe5a9036c4039f9abde0948cd94ef37e136d7ebee`. The earlier build initially failed `DESCRIPTOR_LAUNCHER_BYTES` because provenance was generated before recompilation; [489a983](https://github.com/poteeto/workspace1/commit/489a983e3d1aa6157bbc200f9082a5c1eddd0ee8) orders the rebuild before manifest regeneration without disabling validation.
- Android 15 emulator reports `ro.product.cpu.abilist=x86_64,arm64-v8a` and `ro.dalvik.vm.native.bridge=libndk_translation.so`. Both APKs installed successfully. The real instrumentation reported `ANDROID_NATIVE_BIRTH_AND_ECHILD_PASS`, and the harness reported `ANDROID_KERNEL_NATIVE_BRIDGE_OWNED_SESSION_PASS`.
- [Android KVM diagnostic evidence artifact](https://github.com/poteeto/workspace1/actions/runs/39670697314/artifacts/12380741052), [v178 test-only APK artifact](https://github.com/poteeto/workspace1/actions/runs/39670697314/artifacts/12380790530), [instrumentation APK](https://github.com/poteeto/workspace1/actions/runs/39670697314/artifacts/12380795553).
- [Standard and Low JVM tests 39670083465](https://github.com/poteeto/workspace1/actions/runs/39670083465): **success**. Those JVM tests ran on the preceding v178 source commit; the subsequent commit only changed workflow ordering, not Java or Gradle source.

## Remaining acceptance boundaries

1. The emulator was Android 15 **x86_64 running ARM64 via native bridge**, not a native ARM64 physical phone; real OEM procfs/SELinux policies and hardware remain untested.
2. The instrumentation executes a minimal `/system/bin/sh` subprocess. Full cold BXROOT Ubuntu/tool installation and existing-workspace/session migration **have not passed this test**.
3. These artifacts are **temporary Debug-signed test APKs** and cannot serve as a drop-in same-signature replacement for production E7E3 installations. Do not uninstall/wipe data to install them.
4. PR #2 stays draft; do not automatically merge to main, change historical release signing, or publish an unverified release.
