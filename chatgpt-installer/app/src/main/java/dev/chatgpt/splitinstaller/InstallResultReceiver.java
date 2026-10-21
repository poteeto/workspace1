package dev.chatgpt.splitinstaller;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageInstaller;
import android.os.Build;
import android.widget.Toast;

public final class InstallResultReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        int status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE);
        if (status == PackageInstaller.STATUS_PENDING_USER_ACTION) {
            Intent confirmation;
            if (Build.VERSION.SDK_INT >= 33) {
                confirmation = intent.getParcelableExtra(Intent.EXTRA_INTENT, Intent.class);
            } else {
                confirmation = intent.getParcelableExtra(Intent.EXTRA_INTENT);
            }
            if (confirmation != null) {
                confirmation.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                try {
                    context.startActivity(confirmation);
                    return;
                } catch (Exception e) {
                    save(context, "无法打开系统安装确认：" + e.getMessage());
                    return;
                }
            }
            save(context, "系统没有返回安装确认界面");
        } else if (status == PackageInstaller.STATUS_SUCCESS) {
            save(context, "ChatGPT 安装成功（官方原签名）");
        } else {
            String message = intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE);
            save(context, "安装失败（状态 " + status + "）：" + (message == null ? "未知原因" : message));
        }
    }

    private void save(Context c, String result) {
        c.getSharedPreferences("installer", Context.MODE_PRIVATE)
                .edit().putString("last_result", result).apply();
        Toast.makeText(c, result, Toast.LENGTH_LONG).show();
    }
}
