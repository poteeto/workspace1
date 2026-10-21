# DSHA Android 架构、功能与页面修改地图（2026-10-21）

> 范围：由 `poteeto/workspace1` 的 **main / build173** 源码和本工作分支逐文件核对。只描述仓库中能验证的实现，不把未跑的设备验收写成完成。本文用于后续 Android UI / Web UI / DSH 升级工作，避免重复全库扫描。
>
> UI 工作分支：`ui/deepseek-monochrome-and-architecture-map`（从 `main` 建立）；DSH 0.2.1-rc.2 升级分支 `upgrade/dsh-0.2.1-rc.2`、PR #2 **独立且未合并**，升级版的 Android APK 及老会话迁移尚未验收。

## 1. 一张执行架构图

```text
Android APK (com.dsh.client; :app; Java 17 / XML / Material3)
├─ 原生壳 / 首次引导 / 四栏导航 / 配置 / 备份 / 插件 / PTY / 设备授权
│  ├─ DshaApp（实例与生命周期组合根）
│  ├─ HarnessController + HarnessSessionState + WebLifecycleController
│  ├─ ConfigStore (SharedPreferences) + KeyVault (Android Keystore)
│  └─ Service / DeviceBridge / HttpShellService / Accessibility / ADB / Shizuku
├─ 运行层：ProotBootstrap → RuntimeLauncher / RuntimeExecution
│  ├─ app 私有目录里的 Ubuntu rootfs + bxroot(优先) / proot(回退)
│  ├─ Node 24 / pnpm 10 / @deepseek-ai/dsh + 本地插件 + MCP / tools
│  └─ 会话持久化 / Agent 工作流 / 工具调用 / 模型网关 / Web Server (动态端口)
├─ 会话页面：系统 WebView (Standard) / GeckoView (Low)
│  ├─ DSH React 客户端（上游依赖与锁定补丁）
│  └─ dsh-web-mobile 3.1.0 (TS/TSX/CSS 客户端扩展)
└─ 离线受管资产：Ubuntu、DSH runtime、救援 runtime、Native .so、插件及补丁
```

请勿把 Android Java UI 与 React 聊天网页误作单一主题；修改入口不同，发布要求不同。

## 2. 仓库关键目录和职责

| 路径 | 职责 / 主要入口 |
|---|---|
| `app/src/main/java/com/deepseekharness/app/ui/` | Activity、Fragment、动态生成卡片布局、WebView / PiP / 主题 / 语言 |
| `app/src/main/java/com/deepseekharness/app/core/` | HarnessController、WebLifecycleController、StartupPipeline、ConfigStore、备份/插件/模型等 Repository |
| `app/src/main/java/com/deepseekharness/app/runtime/` | ProotBootstrap、RuntimeLauncher、进程、文件和终端 |
| `app/src/main/java/com/deepseekharness/app/backup/` | 备份、恢复、完整性校验、维护事务和受管资产保护 |
| `app/src/main/java/com/deepseekharness/app/bridge/` | ADB、文件、设备动作和网络桥 |
| `app/src/main/java/com/deepseekharness/app/recovery/` | 独立应急引擎、回切和修复 |
| `app/src/main/java/com/deepseekharness/app/vscreen/` | 实验性虚拟屏 |
| `app/src/main/res/layout/` | 原生 XML 视图（欢迎、主壳、Fragment、对话框等） |
| `app/src/main/res/values[-night]/` | 明暗配色、Material Theme、字符串、字号、尺寸 |
| `app/src/main/res/drawable*/` | 矢量图标、按钮背景、品牌背景、内部品牌 PNG |
| `app/src/main/assets/app-integration/` | Android 对 DSH Web 的服务端扩展：浏览器来源恢复、活动判据等 |
| `app/src/main/assets/builtin-plugins/` | Android computer use、状态展示、web mobile、保护插件等 |
| `app/src/main/assets/builtin-plugins/dsh-web-mobile/src/client/` | 移动 React UI 的组件、交互副作用、响应式 CSS、语言 |
| `tools/dsh-runtime/` | DSH npm 依赖及其锁定版本；main = 0.2.0-rc.2，升级分支 = 0.2.1-rc.2 |
| `tools/mobile-plugin-upstream.lock.json` | dsh-web-mobile 固定 3.1.0 / 上游 commit |
| `tools/apply-mobile-client-patches.mjs` | 对固定上游预构建代码应用 DSHA 补丁；不能直接只改生成产物 |
| `tools/prepare-mobile-plugin.py` | 审核、部署移动插件字节（包含 manifest / hash 约束） |
| `tools/prepare-standard-assets.py` | 构建离线标准受管资产 |
| `app/build.gradle`、`BUILD.md`、`AGENTS.md` | Flavor、签名、打包、构建门禁、维护禁区与验收 |

完整状态归属另见 `docs/module-map.md`。

## 3. 原生 UI 页面、布局和导航

### 首次启动（实际总进度 1～7）
1. `WelcomeActivity.java` + `activity_welcome.xml` + `welcome_page1.xml`：品牌页，ViewPager2，1/7。
2. `welcome_page2.xml`：聊天、终端、插件介绍，2/7。
3. `welcome_page3.xml`：数据、权限、配置介绍，3/7。
4. `OnboardingPrepareActivity.java` + `OnboardingUi.java`：设备架构、空间、安装方式，4/7；由 Java 动态拼装，无 page4 XML。
5. `ExtractActivity.java` + `activity_extract.xml`：真实受管环境安装/检查；不可把展示界面当安装成功。
6. `ModelSetupActivity.java`（原生动态编辑器）：API 地址、协议、模型、凭据；后续设置也共用。
7. `OnboardingReadyActivity.java` + `OnboardingUi.java`：检查实际可用性后进主页。

`MainActivity.java` 的 `ConfigStore.isWelcomed()`、环境就绪门禁决定跳到 Welcome 或 Extract。

### 主界面（非 Compose）
- `activity_main.xml`：60dp 顶栏 / 可选恢复提示 / 1 个 `fragment_container` / 最小 64dp 底部导航。
- `res/menu/bottom_nav_menu.xml`：启动 → 插件 → 设置 → 终端；`MainActivity` 根据选中项切换 Fragment。
- **启动**：`LaunchFragment.java` + `fragment_launch.xml`：进程启动/停止/进入 Web、运行状态、局域网访问、模型入口、诊断日志。
- **插件**：`PluginFragment.java` + `fragment_plugins.xml`，由 `PluginRepository` 驱动安装/查询/启停/导出等。
- **设置**：`SettingsFragment.java` + `fragment_settings.xml` → `InstallFragment`（安装与修复）、`ConfigFragment`（模型、外观、网络等）、`WorkspaceFragment`（数据/备份/文件/技能）、`DeviceGrantsFragment`（ADB/Shizuku/Root/权限）。
- **终端**：`PtyTerminalFragment.java`（真实 PTY，vim/htop/tmux 等）或 `TerminalFragment.java`（简易终端），根据配置/恢复状态选择。

### 其他 Activity（实际存在，优先核对）
- `WebPreviewActivity.java` + `activity_web_preview.xml`：标准系统 WebView，鉴权和下载上传；`GeckoPreviewActivity.java` 是 Low 来源（`src/low`）；共同的 `PictureInPictureActivity` 与 Web 页面状态/来源恢复不可破坏。
- `ModelSetupActivity.java`、`PluginInstallActivity.java`、`UpdateActivity.java`：模型、插件安装与软件更新。
- `DiagnosticActivity.java`、`StartupRecoveryActivity.java`、`RecoveryActivity.java`、`RecoveryWebActivity.java`：故障诊断与应急。
- `NativeDataActivity.java`、`WorkspaceFilesActivity.java`、`StorageActivity.java`、`StorageHelpActivity.java`、`AutomaticBackupActivity.java`、`SkillsActivity.java`：数据、导出、备份与技能。
- `BackgroundTasksActivity.java`、`AgentTasksActivity.java`、`AdbPairActivity.java`、`AccessibilitySetupActivity.java`、`vscreen/VirtualScreenActivity.java`：后台任务、无线配对、无障碍与虚拟屏。

**重要**：`SettingsFragment`、`OnboardingUi`、`ModelSetupActivity`、`CardPage` 等包含 Java 动态 View；只在 res/layout 搜索会漏页面。部分语言文本在 Java 中通过 `UiText` 设置，不全在 strings.xml。

## 4. 功能实现与修改位置

| 功能 | Java / 资源和控制边界 |
|---|---|
| Agent 聊天 | `HarnessController` → `WebLifecycleController` 启动 DSH，WebView 打开实际授权 Web URL；页面 React 源码需查 mobile 插件及 DSH补丁 |
| 模型 / API Key | `ModelSetupActivity` + `DshModelRepository` + `ConfigStore` / `KeyVault`；安全保存 API key，编辑时勿日志打印 |
| DSH 执行引擎 | `runtime/ProotBootstrap` + `RuntimeLauncher`、`RuntimeExecution`；bxroot 优先、确认失败条件时有限 proot 回退 |
| PTY 终端 | `PtyTerminalFragment` + `TerminalSessionOwner` + 原生终端实现 |
| 插件 | `PluginFragment` + `PluginRepository`；内置插件目录与 DSH npm 插件依赖、用户安装事务不同 |
| 手机交互 | `DshaAccessibilityService`、`HttpShellService`、`DeviceBridgeService`、`bridge/`；桥鉴权、授权与系统权限独立 |
| 虚拟屏 | `vscreen/`，需要对应 Android 和 ADB/Shizuku/Root 条件 |
| 备份 / 恢复 | `backup/` + `BackupTask`；维护事务保护旧会话、插件、外部工作区，绝不通过 UI 优化绕过 |
| 网络 / LAN | `LanAuthBridge`、`LanProxyService`、`RuntimeHostPorts`；Web 默认动态本地端口，不要硬编码成 3080 |
| 发布/升级 | `UpdateEngine` / `UpdateRepository`、`app/build.gradle`、签名约束；同包名、历史签名方能覆盖安装 |

## 5. UI 视觉资源归属与本次修复

**已发生的错位**：先前只改了 `res/mipmap-*/` 的桌面图标和 `drawable/dsha_launcher_foreground.xml`，没有修改布局引用，因此截图仍显示蓝色终端标识。

截图上的**大蓝色图标不是** `dsha_brand.png`：`welcome_page1.xml` 实际用的是 `ic_ui2_prompt` + `bg_ui2_mark`；欢迎页顶栏是 `ic_terminal` + `bg_logo`。另外 `activity_main.xml` 仍用了终端图标；背景以及按钮从 `@color/primary` 获得蓝色。独立资源 `drawable-nodpi/dsha_brand.png` 虽然存在，但不能据此认定它是该截图的来源。

本分支目标与落实：
- 欢迎第一页大图、欢迎页顶栏、主页顶栏、`dialog_about.xml`（关于弹窗）及 `AboutFragment.java`（动态关于页）统一改为 **同一套已确认的 DeepSeek 官方鲸鱼矢量**（`dsha_launcher_foreground.xml`）。
- 品牌背景固定黑底，矢量路径固定白色；避免暗色主题下被 Material3 自动 tint 成黑色。
- `values/colors.xml`（白天）及 `values-night/colors.xml`（夜间）移除蓝色主色，改为黑白中性灰；保留 `ok/warn/err` 的语义颜色，不能为了“黑白”抹去危险提示。
- `bg_logo.xml` 保留为**功能图标**的中性主题卡片，`bg_dsha_brand.xml` 是品牌专用黑底，不混用。
- **未改动聊天 React Web UI**：其颜色/CSS/DOM 不吃 Android 的 `colors.xml`。未来要改聊天气泡、消息、顶部栏、输入框或抽屉，需在移动插件 `styles/{base,layout,compat,misc}.css.ts` 与固定上游补丁中处理；改后必须重新生成 `lib/client.js` 并验证 SHA/补丁。

## 6. 页面布局改造时不能遗漏的细节

- **欢迎页**：顶部 XML、3 页 ViewPager XML、底部始终可见的按钮和 dots，以及 Java 中选中态、计数更新、跳转；严格考虑大字号、长文本、滚动和窄屏。
- **主界面**：`MainActivity` Fragment 状态复用、返回栈、下方 BottomNavigationView 与系统栏；恢复横幅可能插入。
- **设置页**：二级菜单由 Java 动态构造；与 ConfigStore 的主题/语言切换保持一一对应。
- **聊天网页**：React DOM 重排、移动 CSS、安全区域 viewport、键盘/IME、附件上传、模型菜单、插件卡片、滚动恢复、侧栏手势和 PiP 共享 Web 实例；不要用脆弱 CSS 覆盖代替可测试的边界。
- **明暗模式**：`ThemeController.java` / `ConfigStore` / `values[-night]` 三者共同决定；按钮底色和 disabled 状态由 `bg_btn_primary.xml` 与 `color/button_primary_text.xml` 决定；请分别检查高对比度。
- **图标**：桌面 adaptive icon、内部品牌图、功能 icon、Web favicon **四套入口**，不可混为一谈；先做引用清单再修改。

## 7. 构建、上线与质量门禁

- 单 Gradle 模块 `:app`，Java17、Material3，Gradle Wrapper 9.3.1 / AGP 9.1.1；Standard = min API 30、系统 WebView；Low = min API 23、GeckoView。二者都只打 `arm64-v8a`。
- `app/build.gradle` main 当前 `versionCode=173`，`versionName=0.2.24-20261014.1308-dsh0.2.0-rc.2`，不是新升级分支的正式产物。
- 关键本机命令：`python3 tools/check-source-hygiene.py`，`python3 tools/check-ui-i18n.py`（具体参数按脚本），`./gradlew :app:testStandardDebugUnitTest :app:testLowDebugUnitTest :app:lintStandardRelease :app:lintLowRelease`；资源/Theme 关联 `app/src/androidTest/java/com/deepseekharness/app/ui/ThemeInstrumentation.java`、`app/src/debug/java/com/deepseekharness/app/ui/LayoutAuditInstrumentation.java` 等。
- 完整 APK 要准备离线 Ubuntu 和 DSH 归档；正式覆盖安装**必须**使用历史发布证书 E7E3，绝不能拿临时 debug 签名冒充或强迫卸载清数据。不可泄露/提交签名私钥。
- 回归优先：首次进入 1/7→7/7；语言中英/明暗主题；标准/兼容版本；主界面底栏、Settings 动态卡片；屏幕旋转/刘海/导航栏/IME/PiP；已有数据升级保存；WebView/Gecko 基础会话和附件；真实 ARM64 设备。
- 本文是**静态源码调查**与分支改动说明；尚未声称 Gradle 全量构建、签名、APK 真机安装或 DSH 升级兼容完成。升级 PR #2 仍有会话兼容与设备验收事项。

## 8. 推荐后续迭代顺序

1. 先确认本分支原生黑白 UI 与品牌矢量的资源正确性；执行 XML/aapt2 + Theme + 导航测试，再出测试 APK。
2. 全量清点 Android 原生子页残留的硬编码蓝色与非语义色，改为统一 token；包括应急、插件、配置、备份及系统状态。
3. 单独开 Web UI 子任务：收集聊天页真实截图，逐页梳理 `dsh-web-mobile` CSS、组件和动态补丁，复用设计 token 而不破坏交互。
4. 将 UI 分支与尚未完成的 0.2.1-rc.2 升级分支做冲突/迁移审查，**先验证后合并**；不要为追版本号跳过老会话读写测试。
5. 最终统一检查应用图标、启动引导、主页、Web 会话、设置页面、系统通知、深浅主题，并验收真实设备。

引用：`AGENTS.md`、`BUILD.md`、`docs/module-map.md`、`app/build.gradle`、`app/src/main/java`、`app/src/main/res`、`tools/dsh-runtime/package.json`、`tools/mobile-plugin-upstream.lock.json`。
