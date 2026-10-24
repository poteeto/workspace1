修复更新 APK 后仍直接进入旧界面的问题。旧的普通运行记录曾使组件更新被跳过；v185 在确认后台版本和数据读写方式相同时，保留旧记录并正常启用新版界面。已有对话、项目、设置保持原位。

保留模型选择、思考强度滑条、上下文环形条、缓存和全部统计详情；若更新未应用，会明确提示当前仍在使用旧界面。

请下载 `dsha-0.2.35.apk` 直接覆盖安装，首次打开将自动准备新版组件。沿用 v180 起固定签名。

同次完整 GitHub 构建、双版单测和 Release Lint、Chromium/Firefox、ARM64 工具检查及安卓隔离升级夹具通过。原 realme Android16 手机和完整模型对话尚未实测；未知的旧运行结果仍保留。

APK SHA256：`0a1f66dadbd2d46ad57b2ead493857c883dec1a287ede066ea52215954a70d72`

附件提供 APK、SHA256 和 verification.json。[验证范围](https://github.com/poteeto/workspace1/blob/upgrade/dsh-0.2.1-rc.2/docs/releases/v0.2.35-build185-upgrade.md)。
