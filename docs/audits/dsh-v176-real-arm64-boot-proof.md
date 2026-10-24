# DSHA v176 APK 所携 DSH 真实启动验收（Linux ARM64）

## 测试定义

此次不是 `npm install` / `dsh --help` / 静态补丁检查，而是从 **GitHub Actions 先前构建的、真实可安装 APK** 中提取 `assets/dsh-runtime.bin`，在 GitHub-hosted 原生 ARM64 Linux 主机上进行真实进程启动、HTTP、浏览器脚本加载以及签名进程监督器协议测试。

### 供应链与输入

- 参照 v176 打包构建：https://github.com/poteeto/workspace1/actions/runs/39635896862
- 输入 APK 的 SHA-256：`c2999e5b5da9d8c26e4bee3ca37c5fdebdd7be5f8d7297e9c85ce5e7952db0a6`
- 输入 APK 大小：`300597760` bytes
- DSH gzip 归档：`148505531` bytes
- 实际运行 DSH：`0.2.1-rc.2`
- **最终全通过的真实启动日志**：https://github.com/poteeto/workspace1/actions/runs/39644675349

## 真实执行结果

| 验证项目 | 真实执行 | 结果 |
|---|---|---|
| APK SHA-256 | 从 GitHub Actions Artifact 读取原生 APK，逐字节校验 | PASS |
| npm 核心来源 | 从 APK 解出 DSH gzip tar，并执行解出的 `dsh/lib/bin.js` | PASS |
| Web profile | 由 Node.js ARM64 拉起 `dsh web --no-open --port PORT` | PASS |
| Host HTTP | 向真实启动的 localhost Web 服务发送 HTTP | PASS，200 |
| 浏览器页面资源 | 请求 HTML `<script src>` 实际编码的模块 URL | PASS，200；脚本约 46345 bytes |
| Node 进程生命周期 | HTTP 请求后进程仍存活；退出时清理 | PASS |
| Native C 监督器 | 直接在 ARM64 Linux 编译当前 `session-launcher.c` | PASS |
| Native 握手 | 本次子进程自读 `/proc/self/stat`、父进程重读 `/proc/PID/stat`、PID/PPID/PGID/SID/starttime 全匹配 | PASS |
| Native peer | UNIX abstract socket 的 `SO_PEERCRED` 进程 ID 和 UID 与出生凭据一致 | PASS |
| 不得提前启动 | 仅建立监督进程，**START 之前**未监听 DSH 端口 | PASS |
| Native START 后真实 Web | 发送 `START` 令牌启动实际 DSH；再请求 HTML 与 JS | PASS |
| Native 退出闭环 | 发送 STOP，收到 `COMMAND_EXITED` 及真正 `ECHILD` 树空证明，最后 COMMIT | PASS |

### 首两轮失败：测试脚本错误，而非 APK 缺少资源

原版 Node smoke 读取 HTML `src="/plugins/?module&amp;rev=..."` 时没有进行浏览器 HTML attribute entity 解码，把真正应该发送的 `&rev=` 误作 `&amp;rev=`，后端按照错误 URL 返回 404；引入 `html.unescape` 等价解码后测试通过。**没有通过屏蔽脚本资源请求让测试变绿**，仍要求 HTTP 200 和有效 JS 内容。

## 覆盖边界（重要）

- 此处运行的是 **真正的 npm DSH 模块和当前 session-launcher.c 源码**，但它们在 **Linux glibc ARM64** 中运行，而不是在 **Android/Bionic 上加载已签名的 `libdsha-session.so`**，也不是经 BXROOT 驱动内核容器。
- **不能**因此宣称已经复现或修复 Android 手机上的 `PROCESS_BIRTH_RECHECK_UNCONFIRMED`。安卓真机的 `/proc` 可读性、SELinux、厂商内核行为、应用 UID 权限及进程启动时序不等同于 GitHub ARM64 runner。
- 没有执行 API 模型请求、账号登录、持久化聊天迁移或 Android WebView 的用户交互。
- 下一步真正需要的证据是同一手机上 `IsolatedInstallProcess.start` 对握手成功后 `/proc/<pid>/stat`、`getsid(pid)` 的**无隐私诊断原因**，不应在无法确认进程身份时粗暴取消身份校验。
- 在取得 Android 真机可重复通过的记录之前，升级 PR 必须保持草稿，避免把 Linux 测试通过误当作整机验收通过。
