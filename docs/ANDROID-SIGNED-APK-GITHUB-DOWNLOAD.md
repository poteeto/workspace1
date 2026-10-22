# DSHA v179+：GitHub Actions 固定签名、验证、ZIP 直链

本仓库的正式发布身份从 v179 起固定为证书 SHA-256：

`52c1746ea586585f43a087fce81cae1e1c89dfa130c09c2b66c64029be7f93a6`

**禁止重新生成密钥或上传任何私钥、口令到公开源码、Issue、PR、Actions artifact 或 GitHub Release。** 任何不匹配此 SHA-256 的 Release 一律阻止。

## 一次性配置（仓库管理员在 GitHub 网页中进行）

打开 `Settings → Secrets and variables → Actions → New repository secret`，添加这 **三个 repository secrets**：

1. `DSHA_KEYSTORE_B64`：把私密备份 ZIP 里的 `DSHA-KEEP-PRIVATE-PUBLISH-KEY-v1.p12` 文件整体 Base64 编码后粘贴（例如在私人设备上运行 `base64 -w0 DSHA-KEEP-PRIVATE-PUBLISH-KEY-v1.p12`，不要复制进公开聊天或日志）。
2. `DSHA_KEYSTORE_PASSWORD`：从私密备份 ZIP 的 `DSHA-SIGNING-KEY-RECOVERY.txt` 取得密钥库密码。
3. `DSHA_KEY_PASSWORD`：从同一私密恢复文件取得密钥密码。

私钥备份文件名：`DSHA-FUTURE-UPDATE-KEY-BACKUP-PRIVATE.zip`。此文件仅应保存于持有人控制的安全位置。它 **不在 GitHub 仓库里**；仅提供公开的证书指纹以便校验。

## 运行 / 下载

工作流：`.github/workflows/build-dsha-rc2-test-apk.yml`

支持推送到 `upgrade/dsh-0.2.1-rc.2` 自动触发，也支持 GitHub `Actions → Build isolated DSHA rc2 Android test APK → Run workflow` 手动启动。

工作流必须按顺序通过：

- 构建完整的 ARM64 非调试 Release APK；验证资源与 runtime；
- 使用同次构建 Debug 测试包进行 Android 模拟器验收；
- 从 **同一次运行** 下载未签名 Release 候选 APK；
- 读取 GitHub Actions Secrets 中的**原有固定签名密钥**，ZIP 对齐、签名；
- 校验包名 `com.dsh.client`、v179、正式证书 SHA-256、APK v3 签名、非调试属性、内置 runtime 完整性和关键文件 CRC；
- 产出 `dsha-0.2.29.apk` 与 `dsha-0.2.29.apk.sha256`；
- 上传名为 **`DSHA-v179-PERMANENTLY-SIGNED-STANDARD-APK`** 的 GitHub Actions ZIP artifact。

打开相应运行的 `Artifacts` 项，点击 `DSHA-v179-PERMANENTLY-SIGNED-STANDARD-APK` 即可**在浏览器直接下载 ZIP**，解压后是已签名可安装 APK（不会误认成 Debug 或 unsigned）。

固定 artifact 的 ZIP 页面路径可在运行完成后构造为：

`https://github.com/poteeto/workspace1/actions/runs/<RUN_ID>/artifacts/<ARTIFACT_ID>`

必须读取**实际生成的**两个 ID，不能事先猜测链接。GitHub Actions ZIP 下载可能要求已登录 GitHub；artifact 30 天到期，并非永久 GitHub Release。

**没有配置齐全部三个 Secrets 时发布任务故意失败（fail closed），不会谎称已签名 ZIP 生成成功。**

## 安装注意

v178 的旧 E7E3 发布签名与 v179 的新签名不同：首次安装必须先备份旧应用资料，再卸载旧包并安装新包。后续同一新密钥的版本可正常覆盖升级。

本流程不自动将私钥发送或提交至 GitHub。将本地签名密钥配置为 GitHub repository secrets 是**一次性必要的管理员操作**；ChatGPT 当前 GitHub 连接器无权操作 repository secrets。
