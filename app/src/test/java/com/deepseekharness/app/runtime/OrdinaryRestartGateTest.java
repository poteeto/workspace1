package com.deepseekharness.app.runtime;

import static org.junit.Assert.*;

import com.deepseekharness.app.backup.*;
import com.deepseekharness.app.util.MaintenanceGate;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.*;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

/** The reported v180 record is history of a run, not a file-changing maintenance operation. */
public class OrdinaryRestartGateTest {
  @Rule public TemporaryFolder temporary = new TemporaryFolder();
  private static final String ID = "8d79deee-7522-4f90-a1c0-719481263a5d";
  private static final String BOOT = "11111111-1111-4111-8111-111111111111\n";
  private final JvmBackupFileSystem fs = new JvmBackupFileSystem();

  private File fixture() throws Exception {
    File files = temporary.newFolder();
    File entry = new File(files, "bounded-guest-active/" + ID);
    Files.createDirectories(entry.toPath());
    Files.writeString(new File(entry, "intent").toPath(), ID + "\n");
    Files.writeString(new File(entry, "identity").toPath(), ID + "\n19743 188183196 19743\n");
    Files.writeString(new File(entry, "protocol").toPath(), "DSHA_OWNED_TREE_V2\n");
    File personal = new File(files, "linux/ubuntu/root/.dsh/sessions/keep.txt");
    Files.createDirectories(personal.getParentFile().toPath());
    Files.writeString(personal.toPath(), "personal chat and configuration must survive");
    return files;
  }

  private void replacementBarrier(File files) throws IOException {
    BoundedGuestSessions.reapExited(fs, files,
        (pid, born) -> { throw new AssertionError("No invented SID closure"); },
        (pid, born) -> { throw new AssertionError("No invented tree closure"); },
        () -> BOOT);
  }

  private static Map<String, String> bytes(File files) throws IOException {
    Map<String, String> result = new TreeMap<>();
    try (var paths = Files.walk(files.toPath())) {
      for (var path : paths.filter(Files::isRegularFile).toList())
        result.put(files.toPath().relativize(path).toString(),
            Base64.getEncoder().encodeToString(Files.readAllBytes(path)));
    }
    return result;
  }

  @Test public void ordinaryReopenDoesNotBecomeMaintenanceOrAlterTheOldRun() throws Exception {
    File files = fixture();
    Map<String, String> before = bytes(files);
    for (int reopened = 0; reopened < 30; reopened++) {
      assertFalse(HostMaintenancePending.inspect(fs, files).blocked);
      assertEquals(ID, BoundedGuestSessions.firstPending(fs, files));
    }
    assertEquals(before, bytes(files));
    assertFalse(new File(files, "bounded-guest-completed/" + ID).exists());
  }

  @Test public void oldFailedRecoveryCheckpointDoesNotLockOrdinaryUse() throws Exception {
    File files = fixture();
    assertThrows(IOException.class, () -> replacementBarrier(files));
    assertTrue(new File(files, BoundedGuestBootRecovery.HOME + "/" + ID + "/checkpoint").isFile());
    Map<String, String> before = bytes(files);
    for (int reopened = 0; reopened < 30; reopened++) {
      assertFalse(HostMaintenancePending.inspect(fs, files).blocked);
      assertEquals(ID, BoundedGuestSessions.firstPending(fs, files));
    }
    assertEquals(before, bytes(files));
  }

  @Test public void realInterruptedRestoreStillBlocksEvenWithOrdinaryHistory() throws Exception {
    File files = fixture();
    File operation = new File(HostOperationArchive.root(files), UUID.randomUUID().toString());
    Files.createDirectories(operation.toPath());
    TransactionMarkers.write(fs, operation, "switching", "TRANSACTION_MARKER");
    Files.writeString(new File(operation, "plan.json").toPath(), "{}");
    Map<String, String> before = bytes(files);
    var check = HostMaintenancePending.inspect(fs, files);
    assertTrue(check.blocked);
    assertEquals("host-data", check.domain);
    assertEquals(operation.getName(), check.operation);
    assertEquals(before, bytes(files));
    Files.delete(new File(operation, "plan.json").toPath());
    check = HostMaintenancePending.inspect(fs, files);
    assertTrue(check.blocked);
    assertEquals("host-data", check.domain);
    assertTrue(check.error.contains("TRANSACTION_PLAN_MISSING"));
  }

  @Test public void reopeningDoesNotAuthorizeDestructiveMaintenance() throws Exception {
    File files = fixture();
    assertFalse(HostMaintenancePending.inspect(fs, files).blocked);
    MaintenanceGate gate = new MaintenanceGate();
    List<String> actions = new ArrayList<>();
    var ports = new MaintenanceGate.Ports() {
      public boolean ownsExecutionTicket() { return true; }
      public MaintenanceGate.Ticket acquireExecutionTicket(String kind) { throw new AssertionError(); }
      public MaintenanceGate.Scope beginWork() { return () -> {}; }
      public void stopTerminals() { actions.add("terminals"); }
      public void stopWeb() { actions.add("web"); }
      public MaintenanceGate.Scope tryEnterMaintenance() { return () -> {}; }
      public void confirmOtherProcesses() throws IOException { replacementBarrier(files); }
      public void releaseRecoveryTools() {}
      public long elapsedRealtime() { return 0; }
      public void pause(long delay) { throw new AssertionError(); }
    };
    assertThrows(IOException.class, () -> gate.exclusive(ports, () -> {
      actions.add("overwrite");
      return null;
    }));
    assertEquals(List.of("terminals", "web"), actions);
    assertFalse(gate.isExclusive());
    assertFalse(gate.isOwner());
    assertTrue(new File(files, "bounded-guest-active/" + ID).isDirectory());
    assertEquals("personal chat and configuration must survive",
        Files.readString(new File(files, "linux/ubuntu/root/.dsh/sessions/keep.txt").toPath()));
    assertFalse(HostMaintenancePending.inspect(fs, files).blocked);
  }

  @Test public void unreadableProcessHistoryIsNotAFileMaintenanceJournal() throws Exception {
    File files = fixture();
    Files.writeString(new File(files, "bounded-guest-active/" + ID + "/protocol").toPath(), "unknown");
    Files.writeString(new File(files, BoundedGuestBootRecovery.HOME).toPath(), "damaged history");
    Map<String, String> before = bytes(files);
    assertFalse(HostMaintenancePending.inspect(fs, files).blocked);
    assertThrows(IOException.class, () -> BoundedGuestSessions.firstPending(fs, files));
    assertEquals(before, bytes(files));
  }
}
