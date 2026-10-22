# GitHub 固定签名与安装包下载

当前发布流程：v180（0.2.30），分支 upgrade/dsh-0.2.1-rc.2。

## 唯一发布身份

用户本轮授权首次生成一把新的 RSA-4096 / PKCS12 发布密钥。GitHub Actions 生成私钥，用仓库 Secret DSHA_SIGNING_MASTER_PASSWORD 加密，密文保存到 ci/github-signing/dsha-permanent-release.p12.gpg；公开指纹保存到 certificate.sha256 和 ci/release-identity.json。密码不进入源码、日志或 artifact。本地私密备份在仓库目录之外，需另行妥善保管。

身份状态从 bootstrap-authorized 只转换一次为 active。active 状态下密文、指纹或密码丢失均停止发布，不重新生成密钥。不同运行的签名任务串行；即使旧构建稍后执行，也从分支读取已持久保存的签名身份。只有密文提交成功后才上传可安装的 APK。

历史 E7E3 与 52c174… 都不是此次新身份。首次成功后的权威指纹以 ci/github-signing/certificate.sha256 为准，后续必须复用。不要再次把状态改回 bootstrap-authorized。

## 下载

工作流 .github/workflows/build-dsha-rc2-test-apk.yml 构建 Standard 非调试候选、验证运行时和双版单测，并用同次 Debug APK 检查 Android 15 模拟器中的原生进程协议。签名任务随后签署同次 Release 候选，检查证书、版本和内容，再上传 DSHA-v180-GITHUB-KEY-SIGNED-STANDARD-APK，包含 dsha-0.2.30.apk 及 SHA-256。Artifact 保留 30 天，下载需登录 GitHub；未签名候选和 Debug 包不能代替正式包。

模拟器的原生进程协议检查不等于 Release APK 的真实手机全功能验收。

## 旧版本维护卡住

用户提供的 v178 / realme RMX5090 / Android 16 日志显示：普通 V2 会话残留 identity、intent、protocol，缺少 tree-empty；试运行本身已闭合。缺少回执不能当作仍存活，也不能当作全部退出。

v180 允许已进入 uncertain 状态的当前拥有者建立持久恢复检查点；仍活动的拥有者继续阻止恢复。同次开机不能清除未知进程树，需先点恢复建立检查点，再真实重启手机，再点恢复。记录整体保存于 bounded-guest-boot-recovery，不移动或删除个人数据，不重放未知命令，不伪造 ECHILD。该路径在手机上的实际验收仍待完成。

界面现在展示具体阻塞域与记录号；导出的错误日志补充维护任务最后阶段、恢复失败详情及进程记录状态，避免旧日志只有 failureRecorded=false 而看不到维护失败。

## 签名迁移

新证书无法直接覆盖手机上不同签名的旧包。请先保留旧应用并导出可验证的数据副本；没有备份不要卸载或清除数据。新签名连续发布使用同一密钥和递增 versionCode。此流程不承诺能对旧签名原地覆盖，也不把代码测试视为旧数据恢复验收。
