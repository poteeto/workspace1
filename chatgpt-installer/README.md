# ChatGPT 官方原签名分包安装器

这个工程将 APKMirror 的 ChatGPT 分包用 Android 原生 \`PackageInstaller.Session\` 安装；**不合并/修改 ChatGPT APK，也不替换 ChatGPT 的签名**。本安装器本身是独立的 APK，使用它自己的构建签名。

## 两种模式

1. **通用工具（默认）**：下载构建产物 \`app-debug.apk\`，手机安装一次，以后在安装器里选择从 APKMirror 获取的 \`.apkm\` 或 \`.apks\`；由系统确认安装 ChatGPT。
2. **真正单文件携带原始分包**：把从 APKMirror 正常下载的合法 \`.apkm\` 文件复制到 \`app/src/main/assets/chatgpt.apkm\`，然后编译，生成的安装器便出现「直接安装内置 ChatGPT」按钮；无需另外选择压缩包。此过程只把原文件作为资源存进安装器，不动其中任何 APK 的签名。

> 注意：单文件只是“自包含安装器”，**不是**将分包合并为一个由 OpenAI 签名的 \`com.openai.chatgpt.apk\`。它仍然需要系统的未知来源授权及安装确认。某些国产 ROM 可能拦截第三方安装。不会绕过手机安全机制。

## 版本与证书

2026-10-21 核实的 APKMirror 版本：ChatGPT **1.2026.286**，版本码 **2628614**，包名 \`com.openai.chatgpt\`。

版本页面：https://www.apkmirror.com/apk/openai/chatgpt/chatgpt-1-2026-286-release/chatgpt-1-2026-286-3-android-apk-download/

APKMirror 公布的签名证书 SHA-256：

\`b24f4bfbb3cf293f938703b9d87027c1102cc36dc4fa206910e08927db40473c\`

安装器会读取 base.apk 的包名及签名证书并拒绝签名不符的包。Android 自己也会检查每个 split 的安装一致性。**不要跳过任何验证**。

## 本地编译

要求 Android SDK 35、JDK 17、Gradle 8.9：

\`\`\`sh
cd chatgpt-installer
gradle :app:assembleDebug
\`\`\`

生成：\`app/build/outputs/apk/debug/app-debug.apk\`

要制作内置分包版，请在编译前本地放入 \`app/src/main/assets/chatgpt.apkm\`，不要把第三方应用二进制公开提交到仓库。若不是从 APKMirror 下载，先核对来源和证书。

## GitHub Actions

\`.github/workflows/build-chatgpt-installer.yml\` 在本分支代码提交后自动尝试构建通用安装器，并将 APK 存为 Actions artifact。**只有 workflow 显示成功且存在 artifact 时才算编译完成。**

## 局限和风险

- 未能在可用沙箱取得 APKMirror 受控下载链接对应的 APKM 文件；因此未内置最新的 ChatGPT 包，也尚未进行真实手机安装验收。
- 目前支持包含 \`base.apk\` 或 \`base-master.apk\` 的标准 ZIP 型 APKM/APKS，过滤不匹配 CPU、DPI、语言的 config split；特殊动态特性/依赖的分包结构可能不兼容。
- APKMirror 的签名证书若因 Google Play 密钥轮换变化，本工具会安全地拒绝，需核实后更新证书。
- 本安装器的调试版签名与 ChatGPT 无关；OpenAI 原始 APK 签名不变。
