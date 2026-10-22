> 历史记录：本轮用户已重新授权由 GitHub Actions 首次生成新固定密钥，后续统一复用。下方 v179 候选证书不再作为当前发布身份；以 [当前流程](../ANDROID-SIGNED-APK-GITHUB-DOWNLOAD.md) 和 ci/github-signing/certificate.sha256 为准。

# DSHA v179：固定新签名正式安装包

2026-10-22。用户明确决定不再追索 E7E3 原签名；本项目从 v179 起采用固定的新 RSA-4096 发布密钥（PKCS12，alias `dsha-publish`）。

- 包名：`com.dsh.client`；versionCode：179；versionName：`0.2.29-20261022.1135-dsh0.2.1-rc.2`。
- 新签名证书 SHA-256：`52c1746ea586585f43a087fce81cae1e1c89dfa130c09c2b66c64029be7f93a6`；后续正式包不得再自行生成另一把钥匙。
- 本轮标准版的非调试 Release APK 由 GitHub Actions run `39721052975` 构建并通过资源和基础模拟器验证；其未签名 APK 在隔离环境使用 Android SDK 36 `apksigner` 与该固定密钥重新签名。
- 实际签名 APK SHA-256：`0e18aac775444b102f45288bb6eb25058a383754dd33012ab73d1d51c49c2332`，字节数 `298174041`；使用 `apksigner verify --min-sdk-version 23` 证明 v1/v2/v3 全部有效，并在 Android 11 条件下证明 v3 有效。
- 实际 `AndroidManifest.xml`、`dsh-runtime.bin`、`offline-rootfs.bin`、`runtime-descriptor.json` 的 ZIP 条目大小/CRC 与通过 CI 的未签名 Release 源包一致。用户指出的设置页“支持”分组两条多余横线已经删除，并添加静态回归校验。
- **安装边界：** 旧 E7E3 应用不能被新签名覆盖。首次迁移必须用户自行备份旧应用数据、卸载旧应用再安装新包；未经实际恢复验收，不保证备份格式或外置文件自动保留。新签名 v179 与其后所有同密钥且版本号递增的发布包可正常覆盖升级。
- 新的 **私钥与口令仅以独立私密备份文件交付用户**，不提交 GitHub，不放入公开 Actions artifact/Release，也不能在此仓库重新生成同名密钥假装兼容。任何未来发布必须使用 `DSHA_KEYSTORE`、`DSHA_KEYSTORE_PASSWORD`、`DSHA_KEY_PASSWORD` 与 `DSHA_KEY_ALIAS=dsha-publish`，Gradle 再核对 `ci/release-identity.json`。
- 本轮未完成用户手机上的安装、迁移或联网服务验收；不能据此宣称真实设备全功能合格。
