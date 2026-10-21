package com.deepseekharness.app.runtime;

import org.junit.*;
import org.junit.rules.TemporaryFolder;
import java.io.File;
import java.util.*;
import static org.junit.Assert.*;

public class RuntimeLauncherTest {
  @Rule public TemporaryFolder temporary = new TemporaryFolder();

  private final RuntimeHostPorts ports = new RuntimeHostPorts();

  @Before
  public void hostSettings() {
    ports.install(
        new RuntimeHostPorts.Provider() {
          public RuntimeHostPorts.Settings snapshot() {
            return new RuntimeHostPorts.Settings("auto", false, true, false);
          }

          public void stage(String value) {}

          public void record(String kind, String detail) {}

          public void failure(Throwable error) {}
        });
  }

  static ContainerRuntime fake() {
    return new ContainerRuntime() {
      public String id() {
        return "fixture";
      }

      public String displayName() {
        return "fixture";
      }

      public boolean available() {
        return true;
      }

      public String unavailableReason() {
        return "";
      }

      public List<String> baseArgv(File root, boolean hardlinks) {
        throw new AssertionError("explicit domain is required");
      }

      public List<String> baseArgv(File root, boolean hardlinks, File domain) {
        return new ArrayList<>(List.of("fixture-runtime", root.getPath()));
      }

      public void applyEnv(ProcessBuilder builder, File base, File lib, File tmp) {
        builder.environment().put("FIXTURE_RUNTIME", "1");
      }

      public void prepare() {}
    };
  }

  private static ContainerRuntime fakeWithId(String id) {
    return new ContainerRuntime() {
      public String id() { return id; }
      public String displayName() { return id; }
      public boolean available() { return true; }
      public String unavailableReason() { return ""; }
      public List<String> baseArgv(File root, boolean links) { return List.of("mock"); }
      public void applyEnv(ProcessBuilder builder, File base, File lib, File tmp) {}
      public void prepare() {}
    };
  }

  @Test
  public void coldToolProbeDoesNotRunInstalledRootQualificationBeforeColdPlan()
      throws Exception {
    // A real APK reported RUNTIME_CAPABILITY_UNCONFIRMED while installing
    // Ubuntu tools. ColdInstallPlan has its own probe/fallback contract; the
    // extra installed-root qualifier never belonged in the cold launch path.
    File root = temporary.newFolder("cold");
    var launcher = new RuntimeLauncher(null, root, root, root, root, ports);
    var spec = LaunchSpec.runtime(fakeWithId("bxroot"))
        .isolated(true).coldTrace(true)
        .coldMode(com.deepseekharness.app.util.ColdInstallPlan.Mode.BXROOT)
        .build();
    // If capable() tried installed-root qualification, context=null and the
    // unpopulated root would fail immediately; no guest command is started.
    assertSame(spec, launcher.capable(spec));
    assertSame(spec, launcher.capable(spec));
  }

  @Test
  public void coldToolProbeRejectsMismatchedFrozenModesWithoutLaunching()
      throws Exception {
    File root = temporary.newFolder("mismatch");
    var launcher = new RuntimeLauncher(null, root, root, root, root, ports);
    for (LaunchSpec candidate : List.of(
        LaunchSpec.runtime(fakeWithId("bxroot")).isolated(true).coldTrace(true)
            .coldMode(com.deepseekharness.app.util.ColdInstallPlan.Mode.PROOT).build(),
        LaunchSpec.runtime(fakeWithId("bxroot")).isolated(true).coldTrace(false)
            .coldMode(com.deepseekharness.app.util.ColdInstallPlan.Mode.BXROOT).build(),
        LaunchSpec.runtime(fakeWithId("bxroot")).isolated(true).coldTrace(true).hardlinks(true)
            .coldMode(com.deepseekharness.app.util.ColdInstallPlan.Mode.BXROOT).build())) {
      var err = assertThrows(java.io.IOException.class, () -> launcher.capable(candidate));
      assertEquals("COLD_FROZEN_ENGINE_MISMATCH", err.getMessage());
    }
  }

  @Test
  public void preparationFailureCompletesTheBoundRecordBeforeAnySpawn() throws Exception {
    File root = temporary.newFolder();
    var fs = new com.deepseekharness.app.backup.JvmBackupFileSystem();
    var record = BoundedGuestSessions.begin(fs, root);
    record.retainCompletion();
    var launcher = new RuntimeLauncher(null, root, root, root, root, new RuntimeHostPorts());
    LaunchSpec spec = LaunchSpec.runtime(fake()).isolated(true).record(record).build();
    IllegalStateException failure =
        assertThrows(IllegalStateException.class, () -> launcher.start("unused", spec));
    assertEquals("RUNTIME_PROVIDER_UNAVAILABLE", failure.getMessage());
    assertTrue(BoundedGuestSessions.recordedCompletion(fs, root, record.id()));
    assertNull(BoundedGuestSessions.firstPending(fs, root));
  }

  @Test
  public void secretsStayInEnvironmentAndSpecDiagnosticsContainOnlyKeys() throws Exception {
    File root = temporary.newFolder();
    var launcher = new RuntimeLauncher(null, root, root, root, root, ports);
    Map<String, String> secrets = new HashMap<>();
    secrets.put("DEEPSEEK_API_KEY", "private-launch-key");
    LaunchSpec spec = LaunchSpec.runtime(fake()).pipedInput(true).environment(secrets).build();
    secrets.put("DEEPSEEK_API_KEY", "modified");
    var builder = launcher.builder("exec dsh web", spec);
    assertEquals("private-launch-key", builder.environment().get("DEEPSEEK_API_KEY"));
    assertFalse(builder.command().toString().contains("private-launch-key"));
    assertFalse(spec.toString().contains("private-launch-key"));
    assertTrue(spec.toString().contains("DEEPSEEK_API_KEY"));
    assertEquals("exec dsh web", builder.command().get(builder.command().size() - 1));
  }

  @Test
  public void launchSpecPreservesNamedChoicesAndRejectsMalformedEnvironment() {
    var spec =
        LaunchSpec.runtime(fake())
            .isolated(true)
            .coldTrace(true)
            .pipedInput(true)
            .bind("/private/payload", "/root/trial")
            .build();
    assertTrue(spec.isolated);
    assertTrue(spec.coldTrace);
    assertTrue(spec.pipedInput);
    assertEquals(1, spec.binds.size());
    assertThrows(UnsupportedOperationException.class, () -> spec.binds.clear());
    assertThrows(
        IllegalArgumentException.class,
        () -> LaunchSpec.runtime(fake()).environment(Map.of("KEY", "bad\0value")).build());
  }
}
