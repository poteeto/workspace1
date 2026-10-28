# DSHA APK 体积审计与安全减重（2026-10-21）

源自对 **官方标准发布版 `v0.2.0-rc2`** 与 **本仓库 DSH `0.2.1-rc.2` Standard Debug 实验包** 的逐条 ZIP 成员分析。

- 审计工具：`tools/report-apk-size.py`
- 真实审计记录：https://github.com/poteeto/workspace1/actions/runs/39610833481
- 实验版基准：https://github.com/poteeto/workspace1/actions/runs/39608426538
- 统计使用 MiB = 1048576 bytes；安卓签名、文件对齐等额外字节计入总数。

## 基线

| APK 内容（ZIP 中实际占用） | 官方 0.2.0 标准 Release | 升级 0.2.1 Debug |
|---|---:|---:|
| 整包大小 | 273.10 MiB | 420.53 MiB |
| 当前 DSH 离线运行包 | 117.01 MiB | 141.63 MiB |
| 旧版本应急 DSH 运行包 | 不单独打包 | 116.99 MiB |
| Ubuntu rootfs | 81.81 MiB | 81.81 MiB |
| Ubuntu 工具 | 28.53 MiB | 28.53 MiB |
| dex 合计 | 16.66 MiB | 20.90 MiB |
| Python / pnpm | 10.78 MiB | 10.78 MiB |

> 这是 Debug 与 Release 的**非同条件比较**，不能把所有增量称为 DSH 依赖增长。单独保留可脱机恢复的旧 DSH 运行包，约占实验包 **117 MiB**；全新 DSH 依赖比官方原版本多约 **24.6 MiB**。

## 实施进展：按用户要求移除旧版 DSH 应急环境

最终选择：**不再在测试 APK 中携带 `0.2.0-rc.2` 的独立 DSH 恢复运行包**。这意味着当前精简版不再提供旧版 DSH 的离线应急启动功能，但 **Android 原生日志查看、数据备份/导出和当前 DSH 的正常环境维护功能仍保留**。不能把本实验版描述成“具有独立 DSH 紧急恢复能力”。

- `app/build.gradle` 的 `BuildConfig.BUNDLED_LEGACY_RECOVERY=false`；Android 构建不再依赖 `prepareRecoveryAssets`，打包资源路径不含 `generated/recoveryAssets`。
- GitHub Actions 不再重新安装或构建旧版 DSH 副本，最终 APK 必须检查 `assets/recovery-dsh-runtime.bin`、`assets/recovery-rootfs.bin`、`assets/recovery-runtime.json` 与 `assets/recovery-overlay/*` **不存在**。
- 单独应急入口在维护与启动恢复页隐藏；直接打开旧入口时，提供备份/日志/当前运行环境维护页面，不会开始安装缺失的应急副本。
- 新 APK `versionCode=174`，测试包名称明确标记 `SLIM-DEBUG-v174`，防止误下载安装旧的 v173 故障包。
- Gradle 压缩 DEX 改变的是 APK ZIP 压缩方式而不是字节码；仍需要真机安装性能测试。
- 旧品牌位图删除，并保留黑底白鲸鱼的原生 UI 整合修改。

## `PATCH_REGISTRY_VERSION` 故障复查

旧实现在 `RuntimeTools.applyPatchChain` 把至少两种原因都显示为同一个含糊的 `PATCH_REGISTRY_VERSION`：Java 常量与包内注册表不一致，以及包内某份补丁声明与已安装 DSH 不一致。

现在：
- 当维护正在从旧 DSH 升级时，先比较**磁盘上安装的 DSH 版本**与 APK 的补丁注册表版本；旧环境不允许套用新补丁，但不会被错误地诊断为“APK 注册表损坏”。
- 常量/注册表真正不匹配时，错误会报告 `apk=`、`registry=`、`installed=` 的具体版本。
- 单项补丁不匹配时，使用独立 `PATCH_RECIPE_VERSION` 和文件名，便于下一次现场反馈。
- GitHub Actions 对**最终 APK 的实际 ZIP 资源**进行检查，逐一验证所有活动补丁 JSON 的 `dshVersion`，而不再仅对源码目录做一致性检查。
- 静态校验与 APK 构建成功不能替代真实手机的升级、安装、会话读写测试。

## 尺寸预期

在之前已经减重至约 **427.8 MB** 的标准 Debug 测试包基础上，去掉 `116.99 MiB` 的旧版应急 DSH 独立运行包，理论上可降到约 **305 MB** 附近（实际数值以新 CI 打包日志为准）。无需为体积优化删除新版 DSH、Ubuntu 基础 rootfs、个人数据管理逻辑或备份功能。

继续保持升级 PR #2 为草稿；严禁通过更换发布签名、卸载现有用户 App 或清除数据来解决升级兼容问题。
