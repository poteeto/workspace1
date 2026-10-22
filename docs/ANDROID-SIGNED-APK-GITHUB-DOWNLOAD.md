# DSHA v179+：仅由 GitHub Actions 生成并管理正式签名

## 原则

- **不使用 ChatGPT 云环境里生成的私钥**。该旧候选签名的证书指纹仅用于历史辨别，不再用于本流程。
- v179 首次正式发布时，在 GitHub Actions 内生成一把 **RSA-4096、PKCS12、alias=dsha-publish** 的新签名密钥。
- 公共仓库绝不提交明文私钥。Actions 用仓库的 **唯一主密码 Secret** 将这把密钥 GPG AES-256 对称加密，把密文持久保存在 `ci/github-signing/dsha-permanent-release.p12.gpg`。
- 每次后续编译，在 GitHub Actions 中解密**同一个**密钥，验证与 `ci/github-signing/certificate.sha256` 和 `ci/release-identity.json` 的证书指纹一致，再签名；密钥或指纹丢失/不匹配时失败，不悄悄换新签名。
- GITHUB_TOKEN 必须有当前分支的 `contents:write` 权限：首次在 GitHub Actions 内生成密钥后，需提交加密备份和公开证书指纹。**只有成功提交密文后才会上传签名 APK**，避免签名无法复用。

## 唯一一次管理员操作：设置一个随机主密码

[打开本仓库 GitHub Actions Secrets](https://github.com/poteeto/workspace1/settings/secrets/actions)，新增 Repository Secret：

- **Name**: `DSHA_SIGNING_MASTER_PASSWORD`
- **Value**: 使用密码管理器随机生成 **不少于 32 字符** 的高强度密码（推荐 48–64 个随机字符）。只填到 GitHub Secrets；不要填写在 PR、Issue、聊天、源码、日志或工作流输入中。

这不是上传旧私钥，而是让 GitHub Actions 在第一次运行时**新建并加密保存自己的永久签名密钥**。不设置该 Secret 时，工作流会明确失败，避免私钥落到公开仓库或生成无法升级的临时签名。**务必妥善备份此主密码**，丢失后将无法解密后续更新所需的私钥。

## GitHub 原生编译、签名与 ZIP 直链

工作流：`.github/workflows/build-dsha-rc2-test-apk.yml`

1. GitHub Actions 以同一份代码编译完整 Standard 版非调试 Release APK。
2. GitHub Actions 执行 Android 模拟器与完整运行时检查。
3. 单独的签名任务从本次 Actions 下载未签名 APK，在 GitHub 上首次生成 / 后续复用上述私钥。
4. 使用 `zipalign` 和 `apksigner`，验证证书、包名、versionCode、非 Debug 属性和关键文件完整性。
5. 第一次使用新签名时，先将仅加密的密钥和新证书指纹提交到 GitHub，再发布可安装的正式 ZIP。
6. 上传 GitHub Actions Artifact：**`DSHA-v179-GITHUB-KEY-SIGNED-STANDARD-APK`**，内含 `dsha-0.2.29.apk` 及其 SHA-256 文件。

构建完成后会出现实际的 `https://github.com/poteeto/workspace1/actions/runs/RUN_ID/artifacts/ARTIFACT_ID` ZIP 下载链接。必须从**实际完成且签名任务成功的构建**取得两个 ID，不得猜测或用 Debug、未签名 APK 冒充。此链接可能要求登录 GitHub，30 天后 artifact 过期。

## 签名迁移注意

GitHub 新生成的证书不同于 v178 历史 E7E3 签名，也不同于此前 ChatGPT 云环境里生成的候选 v179 签名。因此手机上已经安装上述任一种不同证书 APK 时，必须先备份应用数据、卸载旧包，才可安装新的 GitHub 正式签名包。**成功生成后续版本必须继续复用本仓库加密保存的 GitHub 新密钥。**

若首次提交加密备份时因 GitHub Actions 工作流写权限不足而失败，必须先调整仓库的 Workflow permissions / branch rules 使该 job 的 `contents:write` 可提交 `ci/github-signing/`；此时不会发布一个无法保留私钥的正式 APK。
