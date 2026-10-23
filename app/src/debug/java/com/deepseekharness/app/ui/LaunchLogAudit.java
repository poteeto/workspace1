package com.deepseekharness.app.ui;

import android.app.*;
import android.content.*;
import android.os.*;
import android.view.View;
import android.widget.*;
import com.deepseekharness.app.R;
import com.deepseekharness.app.core.ConfigStore;
import com.deepseekharness.app.util.Constants;

/** 真实页面入口、日志滚动以及系统自动小窗偏好；不安装 Ubuntu、不运行 DSH。 */
public final class LaunchLogAudit extends Instrumentation {
  private int checks;
  private void check(boolean value, String reason) {
    checks++;
    if (!value) throw new AssertionError(reason);
  }
  private void ui(Runnable work) {
    Throwable[] failure = {null};
    runOnMainSync(() -> { try { work.run(); } catch (Throwable error) { failure[0] = error; } });
    if (failure[0] != null) throw new AssertionError(failure[0]);
    waitForIdleSync();
  }
  private <T extends Activity> T open(Class<T> type) {
    return type.cast(startActivitySync(new Intent(getTargetContext(), type)
        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)));
  }
  private void home() throws Exception {
    try (var fd = getUiAutomation().executeShellCommand("input keyevent KEYCODE_HOME");
        var input = new ParcelFileDescriptor.AutoCloseInputStream(fd)) {
      while (input.read() != -1) {}
    }
    Thread.sleep(1200);
    waitForIdleSync();
  }
  @Override public void onCreate(Bundle state) { super.onCreate(state); start(); }
  @Override public void onStart() {
    Bundle result = new Bundle();
    java.util.List<Activity> pages = new java.util.ArrayList<>();
    try {
      var context = getTargetContext();
      var prefs = context.getSharedPreferences(Constants.PREFS, Context.MODE_PRIVATE);
      prefs.edit().putBoolean(Constants.KEY_PICTURE_IN_PICTURE, true)
          .remove(Constants.KEY_PICTURE_IN_PICTURE_AUTO_ENTER).commit();
      var store = new ConfigStore(context);
      check(!store.isPictureInPictureAutoEnter(), "LEGACY_SYSTEM_PERMISSION_MUST_NOT_OPT_IN");
      var configHost = open(FragmentSessionTestActivity.class); pages.add(configHost);
      ui(() -> configHost.getSupportFragmentManager().beginTransaction()
          .replace(R.id.fragment_container, new ConfigFragment()).commitNow());
      CompoundButton toggle = configHost.findViewById(R.id.config_picture_in_picture_auto_enter);
      ui(() -> {
        check(!toggle.isChecked(), "NEW_SETTING_MUST_START_OFF");
        toggle.performClick();
        check(new ConfigStore(context).isPictureInPictureAutoEnter(), "OPT_IN_NOT_SAVED");
        toggle.performClick();
        check(!new ConfigStore(context).isPictureInPictureAutoEnter(), "OPT_OUT_NOT_SAVED");
      });
      var picture = open(com.deepseekharness.app.core.PicturePreferenceFixtureActivity.class);
      pages.add(picture);
      Thread.sleep(350); waitForIdleSync();
      ui(() -> {
        check(!picture.onPictureInPictureRequested(), "DISABLED_SYSTEM_REQUEST_ENTERED_PIP");
        if (Build.VERSION.SDK_INT >= 31)
          check(!picture.getPictureInPictureParams().isAutoEnterEnabled(), "SYSTEM_AUTO_ENTER_NOT_DISABLED");
      });
      home();
      ui(() -> check(!picture.isInPictureInPictureMode(), "HOME_CREATED_UNWANTED_WINDOW"));
      ui(picture::finish); pages.remove(picture);
      store.setPictureInPictureAutoEnter(true);
      var enabled = open(com.deepseekharness.app.core.PicturePreferenceFixtureActivity.class);
      pages.add(enabled);
      Thread.sleep(350); waitForIdleSync();
      ui(() -> {
        if (Build.VERSION.SDK_INT >= 31)
          check(enabled.getPictureInPictureParams().isAutoEnterEnabled(), "OPT_IN_DID_NOT_ENABLE_SYSTEM_AUTO_ENTER");
        store.setPictureInPictureAutoEnter(false);
      });
      Thread.sleep(100); waitForIdleSync();
      ui(() -> {
        if (Build.VERSION.SDK_INT >= 31)
          check(!enabled.getPictureInPictureParams().isAutoEnterEnabled(), "OPT_OUT_DID_NOT_REFRESH_EXISTING_PREVIEW");
        store.setPictureInPictureAutoEnter(true);
      });
      Thread.sleep(150);
      home();
      ui(() -> check(enabled.isInPictureInPictureMode(), "OPTED_IN_HOME_DID_NOT_ENTER_PIP"));
      ui(enabled::finish); pages.remove(enabled);
      store.setPictureInPictureAutoEnter(false);
      var home = open(FragmentSessionTestActivity.class); pages.add(home);
      ui(() -> home.getSupportFragmentManager().beginTransaction()
          .replace(R.id.fragment_container, new LaunchFragment()).commitNow());
      ui(() -> {
        check(home.findViewById(R.id.launch_log) == null, "HOME_STILL_CONTAINS_LOG_OUTPUT");
        check(home.findViewById(R.id.launch_safe) != null, "SAFE_START_REMOVED");
        check(home.findViewById(R.id.launch_recovery) != null, "RECOVERY_REMOVED");
      });
      ActivityMonitor monitor = addMonitor(StartupLogActivity.class.getName(), null, false);
      ui(() -> home.findViewById(R.id.launch_logs).performClick());
      StartupLogActivity log = (StartupLogActivity) waitForMonitorWithTimeout(monitor, 5000);
      removeMonitor(monitor);
      check(log != null, "LOG_ENTRY_DID_NOT_OPEN_PAGE"); pages.add(log);
      var update = StartupLogActivity.class.getDeclaredMethod("updateLog", String.class);
      update.setAccessible(true);
      // Pause the timer; drive the actual render method with bounded sample text.
      var handlerField = StartupLogActivity.class.getDeclaredField("handler"); handlerField.setAccessible(true);
      ui(() -> {
        try { ((Handler) handlerField.get(log)).removeCallbacksAndMessages(null); }
        catch (Exception error) { throw new RuntimeException(error); }
      });
      LogScrollView scroll = log.findViewById(R.id.launch_log_scroll);
      TextView output = log.findViewById(R.id.launch_log);
      String text = "sample startup output\n".repeat(1000);
      ui(() -> {
        try { update.invoke(log, text); } catch (Exception error) { throw new RuntimeException(error); }
      });
      Thread.sleep(150); waitForIdleSync();
      ui(() -> {
        check(scroll.getHeight() > 0 && output.getHeight() > scroll.getHeight(), "LOG_NOT_SCROLLABLE");
        check(output.isTextSelectable(), "LOG_COPY_DISABLED");
        scroll.scrollTo(0, 100);
      });
      int reading = scroll.getScrollY();
      ui(() -> {
        try { update.invoke(log, text + "new line\n"); } catch (Exception error) { throw new RuntimeException(error); }
      });
      Thread.sleep(120); waitForIdleSync();
      ui(() -> {
        check(scroll.getScrollY() == reading, "NEW_OUTPUT_INTERRUPTED_READING");
        scroll.scrollTo(0, output.getHeight());
      });
      ui(() -> {
        try { update.invoke(log, text + "new line\ntail\n"); } catch (Exception error) { throw new RuntimeException(error); }
      });
      Thread.sleep(120); waitForIdleSync();
      ui(() -> check(!scroll.canScrollVertically(1), "LOG_TAIL_DID_NOT_FOLLOW"));
      ui(() -> log.findViewById(R.id.startup_log_back).performClick());
      check(log.isFinishing(), "LOG_BACK_DID_NOT_RETURN");
      result.putString("result", "ANDROID_AUTO_PIP_OPT_IN_AND_SEPARATE_LOG_PAGE_PASS");
      result.putInt("checks", checks);
    } catch (Throwable failure) {
      result.putString("failure", android.util.Log.getStackTraceString(failure));
    } finally {
      ui(() -> { for (Activity page : pages) if (!page.isDestroyed()) page.finish(); });
      new ConfigStore(getTargetContext()).setPictureInPictureAutoEnter(false);
      finish(result.containsKey("failure") ? Activity.RESULT_CANCELED : Activity.RESULT_OK, result);
    }
  }
}
