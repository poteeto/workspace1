package com.deepseekharness.app.ui;

import android.content.Intent;
import android.os.Bundle;
import android.view.Gravity;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import com.deepseekharness.app.R;
import com.deepseekharness.app.util.UiText;

/** Infrequent maintenance tools; keep them accessible without occupying bottom navigation. */
public final class AdvancedToolsFragment extends Fragment {
  @Nullable
  @Override
  public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup parent, @Nullable Bundle saved) {
    ScrollView scroll = new ScrollView(requireContext());
    scroll.setFillViewport(true);
    scroll.setBackgroundColor(requireContext().getColor(R.color.surface));
    LinearLayout list = new LinearLayout(requireContext());
    list.setOrientation(LinearLayout.VERTICAL);
    list.setPadding(dp(18), dp(16), dp(18), dp(18));
    scroll.addView(list);

    TextView title = text(UiText.choose("高级工具", "Advanced tools"), 24, R.color.text);
    title.setTypeface(null, android.graphics.Typeface.BOLD);
    list.addView(title);
    TextView description = text(
        UiText.choose("仅在调试和维护时使用；正常对话不需要调整。",
            "Use these only for maintenance and troubleshooting."), 12, R.color.text_secondary);
    LinearLayout.LayoutParams descParams = new LinearLayout.LayoutParams(-1, -2);
    descParams.setMargins(0, dp(6), 0, dp(18));
    list.addView(description, descParams);

    row(list, R.drawable.ic_terminal, UiText.choose("终端", "Terminal"),
        UiText.choose("PTY 命令行、交互程序和简易终端", "PTY shell and interactive command-line tools"),
        () -> open(MainActivity.terminalPage(requireContext()))).setId(R.id.advanced_terminal);
    row(list, R.drawable.ic_ui2_box, UiText.choose("检查与修复环境", "Check and repair environment"),
        UiText.choose("检测组件、按需修复及恢复中断维护", "Check components and recover interrupted maintenance"),
        () -> open(new InstallFragment()));
    row(list, R.drawable.ic_ui_shield, UiText.choose("自检与诊断", "Diagnostics"),
        UiText.choose("运行状态、故障记录和诊断日志", "Runtime status, failures and diagnostic logs"),
        () -> startActivity(new Intent(requireContext(), DiagnosticActivity.class)));
    return scroll;
  }

  private View row(LinearLayout list, int iconRes, String label, String subtitle, Runnable action) {
    LinearLayout row = new LinearLayout(requireContext());
    row.setOrientation(LinearLayout.HORIZONTAL);
    row.setGravity(Gravity.CENTER_VERTICAL);
    row.setMinimumHeight(dp(72));
    row.setPadding(dp(12), dp(10), dp(12), dp(10));
    row.setBackgroundResource(R.drawable.bg_ui2_row);
    row.setClickable(true);
    row.setFocusable(true);
    LinearLayout.LayoutParams rowParams = new LinearLayout.LayoutParams(-1, -2);
    rowParams.bottomMargin = dp(3);
    list.addView(row, rowParams);

    android.widget.ImageView icon = new android.widget.ImageView(requireContext());
    icon.setImageResource(iconRes);
    icon.setImageTintList(android.content.res.ColorStateList.valueOf(requireContext().getColor(R.color.primary)));
    icon.setBackgroundResource(R.drawable.bg_logo);
    icon.setPadding(dp(7), dp(7), dp(7), dp(7));
    icon.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
    row.addView(icon, new LinearLayout.LayoutParams(dp(32), dp(32)));

    LinearLayout words = new LinearLayout(requireContext());
    words.setOrientation(LinearLayout.VERTICAL);
    LinearLayout.LayoutParams wp = new LinearLayout.LayoutParams(0, -2, 1);
    wp.leftMargin = dp(12);
    row.addView(words, wp);
    TextView title = text(label, 13, R.color.text);
    title.setTypeface(null, android.graphics.Typeface.BOLD);
    words.addView(title);
    TextView sub = text(subtitle, 11, R.color.text_secondary);
    LinearLayout.LayoutParams sp = new LinearLayout.LayoutParams(-1, -2);
    sp.topMargin = dp(4);
    words.addView(sub, sp);

    TextView arrow = text("›", 18, R.color.text_muted);
    row.addView(arrow);
    row.setOnClickListener(v -> action.run());
    return row;
  }

  private TextView text(String value, int size, int color) {
    TextView result = new TextView(requireContext());
    result.setText(value);
    result.setTextSize(size);
    result.setTextColor(requireContext().getColor(color));
    result.setIncludeFontPadding(false);
    return result;
  }

  private void open(Fragment page) {
    UiMotion.page(requireContext(), getParentFragmentManager().beginTransaction())
        .replace(R.id.fragment_container, page)
        .addToBackStack("advanced")
        .commit();
  }

  private int dp(int v) {
    return Math.round(v * getResources().getDisplayMetrics().density);
  }
}
