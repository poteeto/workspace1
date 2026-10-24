# 本分支正式签名 APK：本地交付门禁

**状态**：这份流程是正式签名环境准备手册，不代表已交付 APK。仓库 CI 不持有、不上传 E7E3 发布私钥；此前 GitHub Actions 产物只是一份独立 Debug APK，不能直接覆盖原正式版。

## 验收要求
1. 同一分支的软件/安装验证完成，包含 Standard/Low 受影响单测、实际 APK、Android 原生与 DSH 受管运行时检查；用户历史工作区备份与恢复契约不得降级。
2. 真机以非破坏性的既有签名安装覆盖 Android 旧版本，检查冷启动、数据与插件迁移、Web 会话、窗口和终端生命周期。不要先卸载旧应用。
3. 具备**历史 E7E3 APK 发布签名 keystore 和口令**的受信本地构建机器。不得从公开仓库复制 Debug keystore 替代；不要在聊天、GitHub issue、workflow artifact 中提交私钥。
4. 从已固定的 Ubuntu、DSH 0.2.1-rc.2、移动 UI 及 Android 本机编译环境构建全部受管归档；不能用缺包源码或新生成空归档伪装正式环境。

## 本地构建命令

在上述条件就绪后，在已配好 Android SDK / NDK、Java 17、Node 24 与受管运行时资产的本地源码根目录执行：

```bash
export DSHA_KEYSTORE=/secure/path/to/DSHA-ACTUAL-PUBLISH-KEY-debug.keystore
export DSHA_KEYSTORE_PASSWORD=...    # 仅在本机安全提供，禁止写入仓库
export DSHA_KEY_PASSWORD=...
export DSHA_KEY_ALIAS=androiddebugkey
bash tools/build-official-apks.sh standard
```

Low 版单独执行 `bash tools/build-official-apks.sh low`，须另有真实设备兼容性验收。该流程不发布 GitHub Release。

流程先由 Gradle 用 `ci/release-identity.json` 核对实际私钥证书，然后再核对最终 APK：
- 真实包名 `com.dsh.client`、发行 versionCode / versionName 与 flavor；
- `debuggable=false`、APK v1/v2/v3 签名可验证且完整证书为 E7E3；
- 打进 APK 的所有受管运行时文件跟 `runtime-descriptor.json` SHA-256 一致；
- 仅在检查成功时写出 `.apk` 和 `.apk.sha256`，已存在同名文件时拒绝覆盖。

**无历史私钥时的结果是失败而非“换一个签名就算正式版”**。如果真机兼容/数据回归未完成，即使通过签名门禁也仅为候选包，不能对外宣称完全验收。
