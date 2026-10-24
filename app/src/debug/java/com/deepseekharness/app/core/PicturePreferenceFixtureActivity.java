package com.deepseekharness.app.core;

import android.os.Bundle;
import com.deepseekharness.app.R;
import com.deepseekharness.app.ui.PictureInPictureActivity;

/** 调试夹具：用静态页面代替聊天内容，只测试真实宿主/系统小窗，不运行 DSH。 */
public final class PicturePreferenceFixtureActivity extends PictureInPictureActivity {
  private android.app.PictureInPictureParams applied;
  @Override public void setPictureInPictureParams(android.app.PictureInPictureParams value) {
    super.setPictureInPictureParams(value);
    applied = value;
  }
  public android.app.PictureInPictureParams appliedParameters() { return applied; }
  @Override protected boolean pictureInPictureContentReady() { return true; }

  @Override protected void onCreate(Bundle state) {
    super.onCreate(state);
    var lifecycle = com.deepseekharness.app.DshaApp.from(this).harnessSession().lifecycle;
    long generation = lifecycle.beginStart(false, false);
    if (generation > 0) lifecycle.finishStart(generation);
    setContentView(R.layout.activity_startup_log);
  }
}
