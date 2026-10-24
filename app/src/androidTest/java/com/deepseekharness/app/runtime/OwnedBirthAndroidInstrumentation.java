package com.deepseekharness.app.runtime;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Context;
import android.os.Bundle;
import java.util.concurrent.TimeUnit;

/**
 * Runs the real APK-bundled Android/Bionic session supervisor inside the app
 * UID. No user files, network requests, workspaces or package installation.
 * This exercises the EXACT birth identity check that failed on the phone.
 */
public final class OwnedBirthAndroidInstrumentation extends Instrumentation {
  private boolean verifyRestart;
  @Override public void onCreate(Bundle args) {
    super.onCreate(args);
    verifyRestart = args != null && "true".equals(args.getString("restart_verify"));
    start();
  }

  @Override public void onStart() {
    Bundle outcome = new Bundle();
    IsolatedInstallProcess running = null;
    try {
      Context context = getTargetContext().getApplicationContext();
      if (verifyRestart) {
        verifyOrdinaryRestart(context);
        outcome.putString("result", "ANDROID_ORDINARY_REOPEN_WITH_OLD_RECORD_PASS");
        finish(Activity.RESULT_OK, outcome);
        return;
      }
      if (IsolatedInstallProcess.bundledLauncher(context) == null)
        throw new AssertionError("SIGNED_ANDROID_SESSION_LAUNCHER_MISSING");
      var command = new ProcessBuilder(
          "/system/bin/sh", "-c", "/system/bin/echo DSHA_ANDROID_OWNED_SESSION_PASS");
      command.redirectErrorStream(true);
      command.environment().put("DSHA_RUNTIME_ENGINE", "bxroot");
      // Exercise the real NativeTreeControl -> ProcessBirthHandshake ->
      // ProcessIdentity -> peer credentials -> START -> ECHILD path.
      running = IsolatedInstallProcess.start(command, context.getCacheDir(), context);
      boolean done = running.waitFor(25, TimeUnit.SECONDS);
      if (!done) throw new AssertionError("NATIVE_OWNED_PROCESS_DID_NOT_EXIT");
      int status = running.exitValue();
      if (status != 0) throw new AssertionError("OWNED_PROCESS_EXIT_CODE_" + status);
      if (!running.confirmedTreeExit())
        throw new AssertionError("OWNED_PROCESS_TREE_EXIT_NOT_PROVEN");
      // 真正关闭宿主连接，随后由 native 独立清理并落盘；无 COMMIT、无重启。
      var longCommand = new ProcessBuilder("/system/bin/sh", "-c", "/system/bin/sleep 30");
      longCommand.redirectErrorStream(true);
      running = IsolatedInstallProcess.start(longCommand, context.getCacheDir(), context);
      var field = IsolatedInstallProcess.class.getDeclaredField("control");
      field.setAccessible(true);
      ((NativeTreeControl) field.get(running)).close();
      if (!running.waitFor(25, TimeUnit.SECONDS) || !running.confirmedTreeExit())
        throw new AssertionError("DISCONNECTED_NATIVE_TREE_PROOF_NOT_RECOVERED");
      if (BoundedGuestSessions.firstPending(context.getFilesDir()) != null)
        throw new AssertionError("DISCONNECTED_NATIVE_RECORD_LEFT_PENDING");
      outcome.putString("durableRecovery", "ANDROID_DISCONNECTED_NATIVE_PROOF_PASS");
      outcome.putString("result", "ANDROID_NATIVE_BIRTH_AND_ECHILD_PASS");
      finish(Activity.RESULT_OK, outcome);
    } catch (Throwable failure) {
      String message = failure.getClass().getSimpleName() + ": "
          + String.valueOf(failure.getMessage());
      android.util.Log.e("DSHA_ANDROID_BIRTH_TEST", message, failure);
      outcome.putString("result", "ANDROID_NATIVE_BIRTH_AND_ECHILD_FAIL");
      outcome.putString("reason", message.length()>900?message.substring(0,900):message);
      finish(Activity.RESULT_CANCELED, outcome);
    } finally {
      if (running != null) {
        try { running.close(); }
        catch (Throwable unable) {
          android.util.Log.e("DSHA_ANDROID_BIRTH_TEST", "cleanup unconfirmed", unable);
        }
      }
    }
  }

  private void verifyOrdinaryRestart(Context context) throws Exception {
    var files = context.getFilesDir();
    String previous = com.deepseekharness.app.util.Compat.readAll(new java.io.File(files, "restart-fixture-ready"));
    if (!previous.matches("READY [1-9][0-9]*\\n")
        || Integer.parseInt(previous.substring(6).trim()) == android.os.Process.myPid())
      throw new AssertionError("PREVIOUS_APP_PROCESS_WAS_NOT_KILLED");
    var pending = com.deepseekharness.app.backup.HostMaintenancePending.inspect(files);
    if (pending.blocked) throw new AssertionError("ORDINARY_REOPEN_MISREPORTED_AS_MAINTENANCE:" + pending.domain);
    String id = "8d79deee-7522-4f90-a1c0-719481263a5d";
    if (!id.equals(BoundedGuestSessions.firstPending(files)))
      throw new AssertionError("OLD_UNKNOWN_RECORD_NOT_PRESERVED");
    if (new java.io.File(files, "bounded-guest-completed/" + id).exists())
      throw new AssertionError("INTERRUPTION_WAS_FORGED_AS_SUCCESS");
    if (!"KEEP_PERSONAL_DATA\n".equals(com.deepseekharness.app.util.Compat.readAll(
        new java.io.File(files, "restart-personal-sentinel.txt"))))
      throw new AssertionError("PERSONAL_SENTINEL_CHANGED");
    var controller = com.deepseekharness.app.core.HarnessController.get(context);
    if (com.deepseekharness.app.core.EnvironmentAccess.requiresMaintenanceBeforeStart(controller))
      throw new AssertionError("ORDINARY_HISTORY_FORCED_AUTOMATIC_FILE_REPLACEMENT");
    // This test exercises the REAL MainActivity maintenance route. Only missing offline installation
    // is bypassed: this fixture does not pretend to be a full DSH/Ubuntu device acceptance run.
    var intent = new android.content.Intent(context, com.deepseekharness.app.ui.MainActivity.class)
        .putExtra("skip_extract", true).addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK);
    Activity main = startActivitySync(intent);
    waitForIdleSync();
    if (!(main instanceof com.deepseekharness.app.ui.MainActivity) || main.isFinishing()
        || main.findViewById(com.deepseekharness.app.R.id.bottom_nav) == null)
      throw new AssertionError("MAIN_ACTIVITY_STILL_REDIRECTED_TO_MAINTENANCE");
  }
}
