package com.deepseekharness.app.ui;

import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import com.deepseekharness.app.R;
import com.deepseekharness.app.core.HarnessController;

/** 独立的只读实时日志；打开、离开和旋转页面都不改变 Web 的运行状态。 */
public final class StartupLogActivity extends AppCompatActivity {
  private TextView output;
  private LogScrollView scroll;
  private long revision = -1;
  private String language = "";
  private final Handler handler = new Handler(Looper.getMainLooper());
  private final Runnable refresh = new Runnable() {
    @Override public void run() {
      var trace = HarnessController.get(StartupLogActivity.this).startupDiagnostics().snapshot();
      String currentLanguage = getResources().getConfiguration().getLocales().toLanguageTags();
      if (trace.revision != revision || !currentLanguage.equals(language)) {
        updateLog(trace.log.isEmpty() ? getString(R.string.ui_m0025) : trace.log);
        revision = trace.revision;
        language = currentLanguage;
      }
      handler.postDelayed(this, 1000);
    }
  };

  @Override protected void onCreate(Bundle state) {
    super.onCreate(state);
    setContentView(R.layout.activity_startup_log);
    output = findViewById(R.id.launch_log);
    scroll = findViewById(R.id.launch_log_scroll);
    scroll.setViewportBounded(false);
    findViewById(R.id.startup_log_back).setOnClickListener(v -> finish());
    findViewById(R.id.launch_download_logs)
        .setOnClickListener(v -> startActivity(DiagnosticActivity.downloadLogs(this)));
    findViewById(R.id.startup_log_history)
        .setOnClickListener(v -> startActivity(new Intent(this, DiagnosticActivity.class)));
  }

  private void updateLog(String value) {
    boolean follow = scroll.shouldFollowEnd();
    output.setText(value);
    if (follow) scroll.followEndAfterLayout();
  }

  @Override protected void onResume() {
    super.onResume();
    handler.removeCallbacks(refresh);
    handler.post(refresh);
  }

  @Override protected void onPause() {
    handler.removeCallbacks(refresh);
    super.onPause();
  }
}
