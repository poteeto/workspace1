package dev.chatgpt.splitinstaller;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
import java.security.MessageDigest;
import java.util.Locale;

public final class InstallState {
    public static final String PREFS = "installer";
    public static final String PACKAGE = "com.openai.chatgpt";
    public static final String CERT_SHA256 =
            "b24f4bfbb3cf293f938703b9d87027c1102cc36dc4fa206910e08927db40473c";
    public static final String ACTION_RESULT = "dev.chatgpt.splitinstaller.RESULT_UPDATED";
    public static final String REQUEST_SESSION_ID = "installer.request_session_id";
    private InstallState() {}

    public static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    public static PackageInfo installed(Context context) {
        try {
            return context.getPackageManager().getPackageInfo(
                    PACKAGE, PackageManager.GET_SIGNING_CERTIFICATES);
        } catch (PackageManager.NameNotFoundException | SecurityException ignored) {
            return null;
        }
    }

    public static long version(PackageInfo info) {
        return info == null ? -1 : info.getLongVersionCode();
    }

    public static boolean official(PackageInfo info) {
        try {
            if (info == null || info.signingInfo == null) return false;
            Signature[] signatures = info.signingInfo.getApkContentsSigners();
            if (signatures == null || signatures.length != 1) return false;
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(signatures[0].toByteArray());
            StringBuilder sb = new StringBuilder();
            for (byte b : digest) sb.append(String.format(Locale.US, "%02x", b & 0xff));
            return CERT_SHA256.equals(sb.toString());
        } catch (Exception ignored) {
            return false;
        }
    }

    public static String installedStatus(Context context) {
        PackageInfo app = installed(context);
        if (app == null) return "未检测到已安装的 ChatGPT。";
        return "检测到 ChatGPT " + app.versionName +
                (official(app) ? "（官方签名）" : "（签名与 APKMirror 记录不一致）") + "。";
    }

    public static void publish(Context context, String message, boolean finalResult) {
        SharedPreferences.Editor edit = prefs(context).edit().putString("last_result", message);
        if (finalResult) {
            edit.remove("active_session_id")
                .remove("expected_version_code")
                .remove("installed_before_version")
                .remove("install_start_ms");
        }
        edit.commit();
        context.sendBroadcast(new Intent(ACTION_RESULT).setPackage(context.getPackageName()));
    }

    public static boolean isSessionBusy(Context context) {
        SharedPreferences p = prefs(context);
        int id = p.getInt("active_session_id", -1);
        if (id < 0) return false;
        long start = p.getLong("install_start_ms", 0L);
        if (start > 0 && System.currentTimeMillis() - start < 15 * 60_000L) return true;
        p.edit().remove("active_session_id")
                .remove("expected_version_code")
                .remove("installed_before_version")
                .remove("install_start_ms").apply();
        return false;
    }
}
