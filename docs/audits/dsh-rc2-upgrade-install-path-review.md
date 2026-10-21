# DSHA DSH 0.2.1-rc.2 升级：安装链路与兼容性审计

审计范围以 **APK 可打包的 ARM64 Linux DSH 升级链路** 为核心；本报告不会把“Gradle 编译成功”当成“Android 真机正常启动”。

## 真实设备故障与根因

- v173 测试 APK：`PATCH_REGISTRY_VERSION`；Android `Constants.DSH_VERSION` 与升级的资源清单版本不同。v174 已同步常量与补丁清单，并由 APK ZIP 内容校验确认 22 份补丁均为 `0.2.1-rc.2`。
- v174 测试 APK：`LAN_SETTINGS_PATCH_MISMATCH`。**确定根因**：`RuntimeTools.prepareLanSettingsPersistence` 仍在 `dsh-client-ui-settings/lib/client.js` 搜索旧版 `const persistence = ctx.remote.$host.isLoopback ? "host" : "memory";`，但新版 DSH 的真实 npm 代码已完全移除此实现。新版本由 Host RPC `remote.settings.describe/mutate` 和 `settings/document-updated` 统一处理设置持久化。强行应用旧补丁始终失败，且会阻塞安装。
- 修复：新增 `LanSettingsCompatibility.adapt`，按真实 **安装的 DSH** 版本识别旧版/新版设置 API；旧版保留严格旧补丁，`0.2.1-rc.2` 检验 Host 设置读/写/通知三项语义并 **不修改不再存在的旧代码**。未知版本和契约变化拒绝安装，不“自动猜补丁”。
- 新回归测试读取 **npm 发布的实际 0.2.1 包文件**，Standard/Low 两种 JVM 测试覆盖新旧版本、二次执行幂等、契约字段缺失和未知版本拒绝。

## 按实际控制流逐层检查

| 执行环节 | 关键入口 | 对应阻断性验证 |
|---|---|---|
| 依赖来源 | `tools/dsh-runtime/package-lock.json` / `npm ci --os=linux --cpu=arm64` | 不使用 `--force`；精确 DSH 版本 |
| 离线 DSH 归档 | `tools/build-dsh-runtime.py` | tar gzip 源锁、ARM64 ELF、目标文件映射、补丁和 session 适配 |
| Android 受管资源 | `tools/prepare-runtime-descriptor.py` / `managed-runtime-inputs.json` | 325 个受管安装目标，运行时 SHA-256 内容证据；禁止路径穿越 |
| Java/JS/Python/JSON/shell 资源 | `tools/verify-managed-runtime-syntax.py` | 按最终字节做只解析不执行的语法检查（不视为行为测试） |
| 维护候选与冷安装 | `InstallPipeline.repairPatches` / `RuntimeTools.prepare` | 固定按 Android `applyPatchChain` 顺序运行预检 |
| 普通 JS 补丁 | `ManagedPatchChain` / `ExactTextPatch` | 22 个受管配方，69 个精确替换，逐模块顺序/幂等，失败不允许部分发布 |
| 特殊 JS 补丁 | `patchPdfCompatibility`、`patchClientCombos`、`patchBrowserBootstrap` | PDF Worker/主模块/协议；8 项组合缓存；WebView 脚本定位 |
| 设置持久化 | `prepareLanSettingsPersistence` | 新 Host RPC 契约；拒绝植入旧版 loopback 判断 |
| 工作区/会话迁移 | `workspace-directory-policy-patch.json` / `build-dsh-runtime.py` | 受管工作区补丁及打包会话适配器静态锚点 |
| **真实 gzip 归档还原后** | `tools/verify-runtime-archive.py` | 从已构建的 `dsh-runtime.bin` 中还原关键模块，重新运行所有 6 组受管和特化补丁测试；保留 CRLF 原始字节 |
| APK 全部资源 | `tools/verify-apk-runtime-contract.py` | 从最终 APK 流式复核 descriptor 中 **全部** SHA-256；防止资源丢失或源码/包内不一致 |
| Android 原生逻辑 | `testStandardDebugUnitTest` / `testLowDebugUnitTest` | 双 flavor JVM 测试，包含真实 npm 设置模块的回归夹具 |
| APK 发布内容 | `build-dsha-rc2-test-apk.yml` | 版本、22 活动 JSON 补丁、DEX 压缩、Linux/DSH 资源、无旧版 DSH 应急归档 |

## 质量门槛

- 任意 npm、源码锚点、二次执行或打包归档行为不匹配，GitHub Actions 应 **在上传 APK 之前退出失败**。
- 目标是发现 **本次 DSH 版本变化造成的宿主适配问题**，而非宣称数千个类所有业务路径完全无缺陷。
- 同时验证 APK 实际打包的资源而不只是仓库代码；失败时记录模块、锚点及步骤，减少“用户安装后才知道”的循环。
- 即使所有上述项目通过，也不能在没有 ARM64 Android 环境的 CI 中验证厂商 ROM 文件系统权限、进程启动、真实会话数据库迁移、WebView 浏览器生命周期、Model API 登录和本机 ABI/内核兼容。不可凭静态测试自动声明这些已经通过。
- `tools/prepare-runtime-descriptor.py` 的 `READ_COMPATIBILITY` 尚未明确证明 **0.2.0→0.2.1** 会话/JSON 读写兼容；`RuntimeDescriptor.canReadDataWrittenBy` 需要真实读写格式证据，不应把新版本直接写入兼容白名单。
- 用户明确要求不再打包旧版 DSH 应急副本，精简版通过 `BUNDLED_LEGACY_RECOVERY=false` 实现；原生数据备份/日志保留，但 **独立旧版 DSH 恢复服务不再存在**。不要混淆这两者。
- APK Debug 签名与已安装历史发布版可能不同；**不允许为测试要求用户卸载旧包或清除数据**。正式升级仍需原发布证书及真机迁移验收。

## 证据位置

- npm 原始代码兼容性预检：`.github/workflows/audit-runtime-host.yml`
- 真实 gzip 离线归档 + APK 字节验证：`.github/workflows/build-dsha-rc2-test-apk.yml`
- Android 单元测试：`.github/workflows/check-upgrade-android.yml`
- 历史问题和提交记录：`upgrade/dsh-0.2.1-rc.2` / Draft PR #2
