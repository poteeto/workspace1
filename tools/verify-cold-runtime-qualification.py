#!/usr/bin/env python3
"""Fail CI on cold-install/runtime-qualification sequencing regressions.

The guest capability probe must run exactly inside ColdInstallPlan after
unpacked runtime inputs have been prepared. Ordinary business commands keep
their independent and stricter installed-root qualification. This catches the
same premature qualification that stopped Android at 'install offline tools'.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/'app/src/main/java/com/deepseekharness/app'
cold=(JAVA/'runtime/ColdToolsInstaller.java').read_text()
launcher=(JAVA/'runtime/RuntimeLauncher.java').read_text()
plan=(JAVA/'util/ColdInstallPlan.java').read_text()
execution=(JAVA/'runtime/RuntimeExecution.java').read_text()
bundle=(JAVA/'runtime/ColdBundleExtractor.java').read_text()

def block(source,head,end):
    start=source.index(head)
    finish=source.index(end,start+len(head))
    return source[start:finish]
candidate=block(cold,'private static java.util.List<com.deepseekharness.app.util.ColdInstallPlan.Mode> modes(', 'private static String packageFingerprint(')
assert 'boot.packageRuntime()' not in candidate,'cold select prematurely qualifies installed package root'
assert 'boot.hostPorts().engine(boot.ctx, boot.forceProot).runtime' in candidate
assert 'ColdInstallPlan.modes(' in candidate
actual_launch=block(launcher,'private LaunchSpec capable(LaunchSpec spec, boolean packages)', 'static void verifyColdProbeOwnership(')
assert actual_launch.index('if (spec.coldMode != null)') < actual_launch.index('RuntimeEngineQualification.fingerprint(')
assert 'verifyColdProbeOwnership(spec)' in actual_launch
assert 'return spec' in actual_launch
guard=block(launcher,'static void verifyColdProbeOwnership(', 'private static LaunchSpec copyWithRuntime(')
assert 'COLD_FROZEN_ENGINE_MISMATCH' in guard
assert 'spec.coldMode.runtime.equals(spec.runtime.id())' in guard
assert 'spec.coldTrace' in guard
normal=block(execution,'ContainerRuntime packageRuntime()', 'Process trial(')
assert 'launcher.preflight(runtime(), true)' in normal,'ordinary installed package runtime must still qualify'
script=block(plan,'public static String probeScript()', 'public static String probeCommand(')
assert 'RuntimeCapabilityProbe.packages()' in script,'cold probe must cover statx and execveat'
assert 'DSHA_PROBE_STAGE=FSYNC' in script
assert 'DSHA_COLD_RUNTIME_READY' in plan
assert 'COLD_CONFIGURED_CHECK_FAILED_NO_REPLAY' in plan
assert 'result.timedOut' in plan
assert 'result.exited' in plan
assert 'mode == Mode.BXROOT && capabilityFailure(result)' in plan
assert 'boot.installBundledUbuntuTools(onProgress)' in bundle
assert bundle.index('boot.installBundledPython(boot.rootfsDir)') < bundle.index('boot.installBundledUbuntuTools(onProgress)')
assert bundle.index('boot.ensureDshRuntimePatches()') < bundle.index('boot.installBundledUbuntuTools(onProgress)')
assert 'coldMode(mode)' in cold
print('COLD_RUNTIME_QUALIFICATION_ORDER_PASS: prepared candidate, one bounded syscall/package probe, frozen engine, no user-data reset, installed runtime preflight preserved')
