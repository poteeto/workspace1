package com.deepseekharness.app.runtime;

import android.app.Activity;
import android.os.Bundle;
import com.deepseekharness.app.backup.AndroidBackupFileSystem;
import com.deepseekharness.app.util.Constants;
import java.io.File;
import java.nio.charset.StandardCharsets;

/** Emulator-only setup: ordinary long-running work plus the exact shape of the old v180 history. */
public final class OrdinaryRestartFixtureActivity extends Activity {
  private IsolatedInstallProcess running;

  @Override protected void onCreate(Bundle saved) {
    super.onCreate(saved);
    new Thread(() -> {
      try {
        var fs = new AndroidBackupFileSystem();
        File files = getFilesDir().getCanonicalFile();
        String id = "8d79deee-7522-4f90-a1c0-719481263a5d";
        File home = new File(files, "bounded-guest-active");
        if (!home.exists()) fs.directory(home);
        File old = new File(home, id);
        if (!old.exists()) {
          fs.directory(old);
          fs.atomic(old, "intent", (id + "\n").getBytes(StandardCharsets.US_ASCII));
          fs.atomic(old, "identity", (id + "\n19743 188183196 19743\n").getBytes(StandardCharsets.US_ASCII));
          fs.atomic(old, "protocol", "DSHA_OWNED_TREE_V2\n".getBytes(StandardCharsets.US_ASCII));
          try {
            BoundedGuestSessions.reapExited(fs, files,
                (pid, born) -> { throw new AssertionError("No SID closure"); },
                (pid, born) -> { throw new AssertionError("No invented closure"); });
          } catch (java.io.IOException expected) {
            if (!expected.getMessage().contains("REAL_REBOOT_REQUIRED")) throw expected;
          }
        }
        File personal = new File(files, "restart-personal-sentinel.txt");
        if (!personal.exists()) fs.atomic(files, personal.getName(), "KEEP_PERSONAL_DATA\n".getBytes(StandardCharsets.US_ASCII));
        if (!getSharedPreferences(Constants.PREFS, MODE_PRIVATE).edit()
            .putBoolean(Constants.KEY_WELCOMED, true).commit()) throw new AssertionError("PREFERENCE_NOT_SAVED");
        var command = new ProcessBuilder("/system/bin/sh", "-c", "/system/bin/sleep 300");
        command.redirectErrorStream(true);
        running = IsolatedInstallProcess.start(command, getCacheDir(), getApplicationContext());
        fs.atomic(files, "restart-fixture-ready", ("READY " + android.os.Process.myPid() + "\n").getBytes(StandardCharsets.US_ASCII));
      } catch (Throwable failure) {
        android.util.Log.e("DSHA_RESTART_FIXTURE", "Fixture failed", failure);
      }
    }, "ordinary-restart-fixture").start();
  }
}
