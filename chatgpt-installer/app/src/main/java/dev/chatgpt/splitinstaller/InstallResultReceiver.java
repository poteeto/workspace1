package dev.chatgpt.splitinstaller;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageInfo;
import android.content.pm.PackageInstaller;
import android.os.Build;
import android.widget.Toast;

public final class InstallResultReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        SharedPreferences p = InstallState.prefs(context);
        int current = p.getInt("active_session_id", -1);
        int callbackId = intent.getIntExtra(InstallState.REQUEST_SESSION_ID, -1);
        int systemId = intent.getIntExtra(PackageInstaller.EXTRA_SESSION_ID, callbackId);

        // A stale or duplicated callback must never overwrite the current result.
        if (current < 0 || callbackId != current || (systemId >= 0 && systemId != current)) {
            return;
        }

        int status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS,
                PackageInstaller.STATUS_FAILURE);
        if (status == PackageInstaller.STATUS_PENDING_USER_ACTION) {
            InstallState.publish(context, "等待系统安装确认，请在系统弹窗中操作。", false);
            Intent confirmation;
            if (Build.VERSION.SDK_INT >= 33) {
                confirmation = intent.getParcelableExtra(Intent.EXTRA_INTENT, Intent.class);
            } else {
                confirmation = intent.getParcelableExtra(Intent.EXTRA_INTENT);
            }
            if (confirmation == null) {
                finish(context, "系统没有返回安装确认界面，请重新尝试。");
                return;
            }
            try {
                confirmation.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                context.startActivity(confirmation);
            } catch (Exception e) {
                finish(context, "无法打开系统安装确认：" + e.getMessage());
            }
            return;
        }

        long expected = p.getLong("expected_version_code", -1);
        long before = p.getLong("installed_before_version", -1);
        PackageInfo info = InstallState.installed(context);
        long actual = InstallState.version(info);
        boolean verified = InstallState.official(info);
        String rawReason = intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE);
        String reason = (rawReason == null || rawReason.isEmpty()) ? "无详细原因" : rawReason;
        String message;
        if (status == PackageInstaller.STATUS_SUCCESS) {
            if (verified && actual == expected) {
                message = "安装完成，已核实 ChatGPT " + info.versionName + "（官方签名）。";
            } else {
                message = "系统报告安装成功，但未能核实目标版本。"
                        + " 当前状态：" + InstallState.installedStatus(context);
            }
        } else if (verified && actual == expected && expected >= 0) {
            if (before >= 0 && before < expected) {
                message = "已检测到 ChatGPT " + info.versionName
                        + " 成功更新（官方签名）。本安装会话仍返回状态 "
                        + status + "：" + reason + "。";
            } else {
                message = "ChatGPT " + info.versionName + " 已存在且签名正确。"
                        + "本次安装会话返回状态 " + status + "（" + reason
                        + "）。不能确认此次是否重新安装，但无需重复安装已有版本。";
            }
        } else {
            message = "本次安装会话未完成（状态 " + status + "）："
                    + reason + "。\n" + InstallState.installedStatus(context);
        }
        finish(context, message);
    }

    private void finish(Context context, String result) {
        InstallState.publish(context, result, true);
        Toast.makeText(context, result, Toast.LENGTH_LONG).show();
    }
}
