package com.deepseekharness.app.util;

import org.junit.Test;
import java.io.IOException;
import java.util.*;
import static org.junit.Assert.*;

public class ColdInstallPlanTest {
  private static ColdInstallPlan.Observation result(
      int exit, boolean timeout, boolean closed, String text) {
    return new ColdInstallPlan.Observation(exit, timeout, closed, text, text);
  }

  private static ColdInstallPlan.Observation ready(boolean probe) {
    return result(
        0, false, true, probe ? ColdInstallPlan.PROBE_READY : ColdInstallPlan.INSTALL_READY);
  }

  @Test
  public void planContainsOnlyBxrootAndOneConfiguredProot() {
    assertEquals(
        List.of(ColdInstallPlan.Mode.BXROOT, ColdInstallPlan.Mode.PROOT),
        ColdInstallPlan.modes(true, true, true, false));
    assertEquals(
        List.of(ColdInstallPlan.Mode.PROOT_COMPAT), ColdInstallPlan.modes(false, true, true, true));
    assertFalse(ColdInstallPlan.allowDynamicLoaderRetry(true, true, false, true));
  }

  @Test
  public void explicitClosedCapabilityFailureSelectsProotBeforeOneWrite() throws Exception {
    List<String> calls = new ArrayList<>();
    var selected =
        ColdInstallPlan.run(
            ColdInstallPlan.modes(true, true, true, false),
            (mode, probe) -> {
              calls.add(mode + ":" + probe);
              return mode == ColdInstallPlan.Mode.BXROOT
                  ? result(78, false, true, "DSHA_ENGINE_CAPABILITY_UNSUPPORTED static")
                  : ready(probe);
            },
            (mode, probe, observation) -> {});
    assertEquals(ColdInstallPlan.Mode.PROOT, selected);
    assertEquals(List.of("BXROOT:true", "PROOT:true", "PROOT:false"), calls);
  }

  @Test
  public void writeFailureNeverReplaysWithAnotherEngine() {
    List<String> calls = new ArrayList<>();
    assertThrows(
        IOException.class,
        () ->
            ColdInstallPlan.run(
                ColdInstallPlan.modes(true, true, true, false),
                (mode, probe) -> {
                  calls.add(mode + ":" + probe);
                  return probe
                      ? ready(true)
                      : result(78, false, true, "DSHA_BXROOT_ENGINE_FAILURE");
                },
                (mode, probe, observation) -> {}));
    assertEquals(List.of("BXROOT:true", "BXROOT:false"), calls);
  }

  @Test
  public void genericFailureTimeoutAndUnknownTreeStopBeforeSecondProbe() {
    for (var failure :
        List.of(
            result(139, false, true, "crash"),
            result(78, true, true, "DSHA_ENGINE_CAPABILITY_UNSUPPORTED"),
            result(78, false, false, "DSHA_ENGINE_CAPABILITY_UNSUPPORTED"))) {
      List<ColdInstallPlan.Mode> calls = new ArrayList<>();
      assertThrows(
          IOException.class,
          () ->
              ColdInstallPlan.run(
                  ColdInstallPlan.modes(true, true, true, false),
                  (mode, probe) -> {
                    calls.add(mode);
                    return failure;
                  },
                  (mode, probe, value) -> {}));
      assertEquals(List.of(ColdInstallPlan.Mode.BXROOT), calls);
    }
  }

  @Test
  public void configuredOverlayOnlyChecksWithoutReinstalling() throws Exception {
    List<Boolean> calls = new ArrayList<>();
    assertEquals(
        ColdInstallPlan.Mode.BXROOT,
        ColdInstallPlan.runConfigured(
            ColdInstallPlan.modes(true, true, true, false),
            (mode, probe) -> {
              calls.add(probe);
              return result(
                  0,
                  false,
                  true,
                  ColdInstallPlan.PROBE_READY + "\n" + ColdInstallPlan.INSTALL_READY);
            },
            (mode, probe, observation) -> {}));
    assertEquals(List.of(true), calls);
  }

  @Test
  public void staticQualificationsAreBeforeTheReadyMarkerAndNoDpkgWrite() {
    String script = ColdInstallPlan.probeScript();
    assertTrue(script.indexOf("ldconfig.real") < script.indexOf(ColdInstallPlan.PROBE_READY));
    assertTrue(script.contains("dpkg-deb") && script.contains("--version"));
    assertFalse(script.contains("dpkg -i"));
  }

  @Test
  public void configuredColdProbeFallsBackOnlyAfterExplicitClosedCapabilityRejection()
      throws Exception {
    var observed = new ArrayList<String>();
    var modes = ColdInstallPlan.modes(true, true, true, false);
    var selected = ColdInstallPlan.runConfigured(
        modes,
        (mode, probe) -> {
          observed.add(mode.name() + ":probe=" + probe);
          return mode == ColdInstallPlan.Mode.BXROOT
              ? result(78, false, true, "DSHA_ENGINE_CAPABILITY_UNSUPPORTED execveat")
              : result(0, false, true,
                  ColdInstallPlan.PROBE_READY + "\\n" + ColdInstallPlan.INSTALL_READY);
        },
        (mode, probe, outcome) -> {});
    assertEquals(ColdInstallPlan.Mode.PROOT, selected);
    assertEquals(List.of("BXROOT:probe=true", "PROOT:probe=true"), observed);
  }

  @Test
  public void configuredColdProbeRejectsUnconfirmedCapabilityWithoutEngineReplay() {
    var observed = new ArrayList<String>();
    var modes = ColdInstallPlan.modes(true, true, true, false);
    assertThrows(IOException.class, () -> ColdInstallPlan.runConfigured(
        modes,
        (mode, probe) -> {
          observed.add(mode.name());
          return result(125, false, true,
              "RUNTIME_CAPABILITY_UNCONFIRMED: package fingerprint unknown");
        },
        (mode, probe, outcome) -> {}));
    assertEquals(List.of("BXROOT"), observed);
  }

  @Test
  public void coldConfiguredProbeOwnsCompleteEngineCapabilityQualification() {
    String command = ColdInstallPlan.probeScript();
    assertTrue(command.contains("DSHA_ENGINE_PROBE_STAGE=SHELL"));
    assertTrue(command.contains("DSHA_ENGINE_PROBE_STAGE=STATX_BEGIN"));
    assertTrue(command.contains("DSHA_ENGINE_PROBE_STAGE=EXECVEAT_CHILD"));
    assertTrue(command.contains("DSHA_ENGINE_CAPABILITY_READY"));
    assertTrue(command.contains("DSHA_ENGINE_PACKAGE_CAPABILITY_READY"));
    assertTrue(command.indexOf("DSHA_ENGINE_CAPABILITY_READY")
        < command.indexOf(ColdInstallPlan.PROBE_READY));
    assertTrue(command.indexOf("DSHA_ENGINE_PACKAGE_CAPABILITY_READY")
        < command.indexOf(ColdInstallPlan.PROBE_READY));
    assertFalse(command.contains("dpkg -i"));
    assertFalse(command.contains("apt install"));
  }

  @Test
  public void prootCompatibilityProbeKeepsPackageChecksWithoutBxrootSyscallConstraint() {
    String bxroot = ColdInstallPlan.probeScript(ColdInstallPlan.Mode.BXROOT);
    assertTrue(bxroot.contains("DSHA_ENGINE_PROBE_STAGE=STATX_BEGIN"));
    assertTrue(bxroot.contains("DSHA_ENGINE_PROBE_STAGE=EXECVEAT_CHILD"));
    String proot = ColdInstallPlan.probeScript(ColdInstallPlan.Mode.PROOT);
    assertFalse(proot.contains("DSHA_ENGINE_PROBE_STAGE=STATX_BEGIN"));
    assertFalse(proot.contains("DSHA_ENGINE_PROBE_STAGE=EXECVEAT_CHILD"));
    assertTrue(proot.contains("DSHA_ENGINE_PACKAGE_CAPABILITY_READY"));
    assertTrue(proot.contains(ColdInstallPlan.PROBE_READY));
    assertEquals(proot, ColdInstallPlan.probeScript(ColdInstallPlan.Mode.PROOT_COMPAT));
    String name = "/root/.dsha-cold-probe-12345678-1234-1234-1234-1234567890ab";
    assertTrue(ColdInstallPlan.probeCommand(name, ColdInstallPlan.Mode.PROOT)
        .contains("DSHA_ENGINE_PACKAGE_CAPABILITY_READY"));
    assertThrows(IllegalArgumentException.class,
        () -> ColdInstallPlan.probeCommand(name, ColdInstallPlan.Mode.PROROOT));
  }

  @Test
  public void failedPreferenceCommitCannotPublishReady() {
    List<String> calls = new ArrayList<>();
    assertThrows(
        IOException.class,
        () ->
            ColdInstallPlan.publishReady(
                () -> {
                  throw new IOException("unavailable");
                },
                () -> calls.add("ready")));
    assertTrue(calls.isEmpty());
  }
}
