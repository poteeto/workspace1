package dev.chatgpt.splitinstaller;

import android.app.Activity;
import android.app.PendingIntent;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageInstaller;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

public final class MainActivity extends Activity {
    private static final int PICK = 42;
    private static final String CHATGPT_PACKAGE = "com.openai.chatgpt";
    // APKMirror's OpenAI/Google Play app-signing certificate, not the installer's key.
    private static final String SIGNER_SHA256 =
            "b24f4bfbb3cf293f938703b9d87027c1102cc36dc4fa206910e08927db40473c";
    private static final long MAX_ARCHIVE = 300L * 1024 * 1024;
    private static final long MAX_APK = 250L * 1024 * 1024;
    private static final long MAX_TOTAL = 700L * 1024 * 1024;
    private TextView output;
    private File pendingArchive;
    private boolean busy;
    private boolean permissionPageOpen;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        int padding = (int) (24 * getResources().getDisplayMetrics().density);
        panel.setPadding(padding, padding, padding, padding);
        ScrollView scroller = new ScrollView(this);
        scroller.addView(panel);
        setContentView(scroller);

        TextView heading = new TextView(this);
        heading.setText("ChatGPT 官方签名安装器");
        heading.setTextSize(22);
        heading.setGravity(Gravity.CENTER_HORIZONTAL);
        panel.addView(heading, new LinearLayout.LayoutParams(-1, -2));

        TextView info = new TextView(this);
        info.setText("\n支持 APKMirror 的 .apkm 和 Bundletool/SAI 的 .apks。\n"
                + "使用 Android 系统分包安装，不修改、不重新签名 ChatGPT。\n"
                + "最终仍需确认系统的“允许安装未知应用”提示。\n");
        panel.addView(info, new LinearLayout.LayoutParams(-1, -2));

        Button pick = new Button(this);
        pick.setText("选择 APKS / APKM 文件并安装");
        panel.addView(pick, new LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT));
        pick.setOnClickListener(v -> openPicker());

        try {
            if (Arrays.asList(getAssets().list("")).contains("chatgpt.apkm")) {
                Button embedded = new Button(this);
                embedded.setText("直接安装内置 ChatGPT");
                panel.addView(embedded);
                embedded.setOnClickListener(v -> {
                    if (busy) return;
                    busy = true;
                    say("正在读取内置安装包……");
                    new Thread(() -> {
                        try (InputStream in = getAssets().open("chatgpt.apkm")) {
                            File f = copyArchive(in);
                            runOnUiThread(() -> { busy = false; pendingArchive = f; installWhenPermitted(); });
                        } catch (Exception e) { failure(e); }
                    }).start();
                });
            }
        } catch (Exception e) {
            // No embedded APK is normal for the generic installer.
        }
        output = new TextView(this);
        output.setTextSize(15);
        output.setText("\n就绪。");
        panel.addView(output);
    }

    private void say(String message) {
        runOnUiThread(() -> { if (output != null) output.setText("\n" + message); });
    }

    private void openPicker() {
        if (busy) return;
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("*/*");
        startActivityForResult(intent, PICK);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != PICK || resultCode != RESULT_OK || data == null || data.getData() == null) return;
        busy = true;
        say("正在读取并检查安装包……");
        Uri uri = data.getData();
        new Thread(() -> {
            try (InputStream in = getContentResolver().openInputStream(uri)) {
                if (in == null) throw new Exception("无法打开所选文件");
                File file = copyArchive(in);
                runOnUiThread(() -> { busy = false; pendingArchive = file; installWhenPermitted(); });
            } catch (Exception e) { failure(e); }
        }).start();
    }

    private File copyArchive(InputStream in) throws Exception {
        File file = new File(getCacheDir(), "chatgpt-input.apkm");
        long copied = 0;
        try (OutputStream out = new FileOutputStream(file)) {
            byte[] b = new byte[65536];
            int n;
            while ((n = in.read(b)) != -1) {
                copied += n;
                if (copied > MAX_ARCHIVE) throw new Exception("压缩包超过 300 MB 安全限制");
                out.write(b, 0, n);
            }
        }
        if (copied == 0) throw new Exception("文件为空");
        return file;
    }

    private void installWhenPermitted() {
        if (busy || pendingArchive == null) return;
        if (!getPackageManager().canRequestPackageInstalls()) {
            if (!permissionPageOpen) {
                permissionPageOpen = true;
                say("请允许本安装器安装未知应用，然后返回这里。");
                Intent settings = new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                        Uri.parse("package:" + getPackageName()));
                startActivity(settings);
            }
            return;
        }
        File file = pendingArchive;
        pendingArchive = null;
        busy = true;
        say("正在验证 ChatGPT 官方签名并准备分包……");
        new Thread(() -> {
            try { stage(file); }
            catch (Exception e) { failure(e); }
            finally { busy = false; }
        }).start();
    }

    @Override
    protected void onResume() {
        super.onResume();
        String last = getSharedPreferences("installer", MODE_PRIVATE).getString("last_result", null);
        if (last != null) {
            getSharedPreferences("installer", MODE_PRIVATE).edit().remove("last_result").apply();
            say(last);
        }
        if (permissionPageOpen && getPackageManager().canRequestPackageInstalls()) {
            permissionPageOpen = false;
            installWhenPermitted();
        }
    }

    private void stage(File archive) throws Exception {
        File baseForCheck = new File(getCacheDir(), "chatgpt-base-check.apk");
        try (ZipFile zip = new ZipFile(archive)) {
            List<ZipEntry> all = new ArrayList<>();
            ZipEntry base = null;
            for (ZipEntry e : Collections.list(zip.entries())) {
                if (e.isDirectory() || !e.getName().toLowerCase(Locale.ROOT).endsWith(".apk")) continue;
                String shortName = shortName(e);
                if (e.getSize() > MAX_APK) throw new Exception("APK 文件过大：" + shortName);
                all.add(e);
                if (shortName.equals("base.apk") || shortName.equals("base-master.apk")) base = e;
            }
            if (base == null) throw new Exception("压缩包缺少 base.apk（不是有效的 APKS/APKM）");
            if (all.size() > 100) throw new Exception("分包数量异常：" + all.size());

            try (InputStream in = zip.getInputStream(base); OutputStream out = new FileOutputStream(baseForCheck)) {
                transferLimited(in, out, MAX_APK);
            }
            verifyOfficialSignature(baseForCheck);

            List<ZipEntry> selected = selectSplits(all, base);
            long total = 0;
            for (ZipEntry e : selected) {
                if (e.getSize() > 0) total += e.getSize();
                if (total > MAX_TOTAL) throw new Exception("分包大小超过安全限制");
            }

            PackageInstaller pi = getPackageManager().getPackageInstaller();
            PackageInstaller.SessionParams params =
                    new PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL);
            params.setAppPackageName(CHATGPT_PACKAGE);
            int sessionId = pi.createSession(params);
            PackageInstaller.Session session = pi.openSession(sessionId);
            boolean committed = false;
            try {
                Set<String> used = new HashSet<>();
                int index = 0;
                for (ZipEntry e : selected) {
                    String filename = shortName(e);
                    if (!used.add(filename)) throw new Exception("重复的 APK 文件名：" + filename);
                    say("正在准备 " + (++index) + "/" + selected.size() + "：" + filename);
                    try (InputStream in = zip.getInputStream(e);
                         OutputStream out = session.openWrite(filename, 0, -1)) {
                        transferLimited(in, out, MAX_APK);
                        session.fsync(out);
                    }
                }
                Intent callback = new Intent(this, InstallResultReceiver.class);
                PendingIntent sender = PendingIntent.getBroadcast(
                        this, 1436, callback, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_MUTABLE);
                session.commit(sender.getIntentSender());
                committed = true;
                say("已提交系统安装器，请在弹出的系统界面确认安装。");
            } finally {
                if (!committed) session.abandon();
                session.close();
            }
        } finally {
            baseForCheck.delete();
        }
    }

    private void verifyOfficialSignature(File base) throws Exception {
        PackageInfo info = getPackageManager().getPackageArchiveInfo(
                base.getAbsolutePath(), PackageManager.GET_SIGNING_CERTIFICATES);
        if (info == null || !CHATGPT_PACKAGE.equals(info.packageName)) {
            throw new Exception("文件包名不是官方 ChatGPT：" +
                    (info == null ? "无法解析 APK" : info.packageName));
        }
        if (info.signingInfo == null) throw new Exception("APK 签名缺失");
        Signature[] signatures = info.signingInfo.getApkContentsSigners();
        if (signatures == null || signatures.length != 1) {
            throw new Exception("APK 签名者数量异常");
        }
        byte[] hash = MessageDigest.getInstance("SHA-256").digest(signatures[0].toByteArray());
        StringBuilder hex = new StringBuilder();
        for (byte b : hash) hex.append(String.format(Locale.US, "%02x", b & 0xff));
        if (!SIGNER_SHA256.equals(hex.toString())) {
            throw new Exception("签名证书不匹配 APKMirror 公布的 ChatGPT 官方签名。\n实际：" + hex);
        }
        say("已验证官方签名，ChatGPT 版本：" + info.versionName);
    }

    private List<ZipEntry> selectSplits(List<ZipEntry> all, ZipEntry base) throws Exception {
        List<ZipEntry> selected = new ArrayList<>();
        List<ZipEntry> architecture = new ArrayList<>();
        List<ZipEntry> densities = new ArrayList<>();
        selected.add(base);
        String language = Locale.getDefault().getLanguage().toLowerCase(Locale.ROOT);
        for (ZipEntry e : all) {
            if (e == base) continue;
            String name = shortName(e).toLowerCase(Locale.ROOT);
            if (name.equals("base.apk") || name.equals("base-master.apk")) continue;
            if (architectureId(name) != null) { architecture.add(e); continue; }
            if (densityValue(name) != -1) { densities.add(e); continue; }
            Matcher lang = Pattern.compile("(?:split[_-])?config[._-]([a-z]{2})(?:[-_]r[a-z]{2})?\\.apk$")
                    .matcher(name);
            if (lang.find()) {
                String l = lang.group(1);
                if (l.equals(language) || l.equals("en")) selected.add(e);
                continue;
            }
            // Keep feature APKs and all otherwise-unrecognized splits.
            selected.add(e);
        }

        if (!architecture.isEmpty()) {
            ZipEntry best = null;
            outer: for (String deviceAbi : Build.SUPPORTED_ABIS) {
                for (ZipEntry e : architecture) {
                    if (deviceAbi.replace('-', '_').equals(architectureId(shortName(e)))) {
                        best = e;
                        break outer;
                    }
                }
            }
            if (best == null) throw new Exception("没有匹配本机 CPU 的 APK 分包");
            selected.add(best);
        }
        if (!densities.isEmpty()) {
            int target = getResources().getDisplayMetrics().densityDpi;
            ZipEntry best = null;
            int bestScore = Integer.MAX_VALUE;
            for (ZipEntry e : densities) {
                int d = densityValue(shortName(e).toLowerCase(Locale.ROOT));
                int score = Math.abs(d - target) * 2 + (d < target ? 1 : 0);
                if (score < bestScore) { best = e; bestScore = score; }
            }
            if (best != null) selected.add(best);
        }
        return selected;
    }

    private static String architectureId(String name) {
        String s = name.toLowerCase(Locale.ROOT).replace('-', '_');
        for (String abi : new String[] {"arm64_v8a", "armeabi_v7a", "x86_64", "x86"}) {
            if (s.contains(abi)) return abi;
        }
        return null;
    }

    private static int densityValue(String name) {
        String s = name.toLowerCase(Locale.ROOT);
        Matcher m = Pattern.compile("(?:^|[^0-9])(\\d{3,4})dpi(?:\\.|_|$)").matcher(s);
        if (m.find()) return Integer.parseInt(m.group(1));
        if (s.contains("xxxhdpi")) return 640;
        if (s.contains("xxhdpi")) return 480;
        if (s.contains("xhdpi")) return 320;
        if (s.contains("hdpi")) return 240;
        if (s.contains("mdpi")) return 160;
        if (s.contains("ldpi")) return 120;
        return -1;
    }

    private static String shortName(ZipEntry e) {
        String s = e.getName().replace('\\', '/');
        return s.substring(s.lastIndexOf('/') + 1);
    }

    private static void transferLimited(InputStream in, OutputStream out, long limit) throws Exception {
        byte[] buf = new byte[64 * 1024];
        long size = 0;
        int n;
        while ((n = in.read(buf)) != -1) {
            size += n;
            if (size > limit) throw new Exception("解压后的 APK 超过大小限制");
            out.write(buf, 0, n);
        }
    }

    private void failure(Exception e) {
        runOnUiThread(() -> {
            busy = false;
            say("出错：" + e.getMessage());
        });
    }
}
