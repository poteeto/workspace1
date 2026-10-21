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

## 已实施的低风险压缩

- 在 `app/build.gradle` 的 APK packaging 中启用 `dex.useLegacyPackaging = true`。仅改变 DEX 的 APK ZIP 压缩方式，**不移除 DEX、修改字节码、删权限或改变运行环境**。Android 30+ 安装时可能需要额外解压空间与时间，必须进行实际安装测试。
- 删除已经由同一官方 DeepSeek 矢量取代、且全 `app/src` 确认无资源引用的 `drawable-nodpi/dsha_brand.png`，约 360 KiB。
- 新 CI 必须检查全部 `classes*.dex` 为 DEFLATE，并且新 DSH 与旧恢复包两者都存在；任何一步失败即停止上传测试 APK。
- 用 `tools/verify-monochrome-ui.py` 防止新版布局又回到旧品牌位图或自动染色。

## 不可通过删包换体积的内容

- `assets/offline-rootfs.bin`：完整离线 Linux 用户空间。
- `assets/dsh-runtime.bin`：实际 DSH 核心。
- `assets/recovery-dsh-runtime.bin`：独立的老版本应急恢复环境，必要时供受限界面继续导出/恢复数据。**不能在无可验证替代实现前删去**。
- `assets/ubuntu-tools.bin`、Python、pnpm、受管策略、签名与凭证保护相关资产：需要实际依赖验证，不做静态猜测删减。

## 后续体积路线（不在这次实验包冒险实施）

1. 对两个版本 DSH 运行包按文件内容 SHA-256 审计重复模块，研究可以逐文件校验的离线差量重建，不修改旧版本应急镜像的逻辑身份。
2. 如采用差量形式，应在设备上完成复原 SHA-256 全等、掉电中断恢复、存储不足处理及 Android 6/11+ 的冷启动与会话数据迁移测试；才能替换原有 117 MiB 独立包。
3. 在保留历史 E7E3 签名的前提下对照同一 flavor 的正式包。严禁为了缩小上传包用临时签名冒充官方可覆盖安装版本。
4. WebView / React UI 与 Android 原生 UI 属于不同渲染层，本次只统一原生主题和品牌；未把静态主题检查冒充真机视觉验收。
