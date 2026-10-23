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
  @Override public void onCreate(Bundle args) {
    super.onCreate(args);
    start();
  }

  @Override public void onStart() {
    Bundle outcome = new Bundle();
    IsolatedInstallProcess running = null;
    try {
      Context context = getTargetContext().getApplicationContext();
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
}
