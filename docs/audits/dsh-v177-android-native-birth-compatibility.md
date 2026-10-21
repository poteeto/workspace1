# DSHA v177 — Android 原生启动器身份复核兼容改造与验收边界

## 设备上实际报告的失败

v176 在更新环境时停在「检查离线安装运行方式：BXROOT」：
`PROCESS_BIRTH_RECHECK_UNCONFIRMED`。

- 发生于 `IsolatedInstallProcess.start` 在收到已签名启动器读出的 `/proc/self/stat` 出生证据后，尝试父侧访问 `/proc/<pid>/stat` 并备用 `getsid(pid)`。
- 该 Java 启动器类与官方 `DSH-APP/DSHA` main **字节一致**，错误未必是该源文件变化造成；升级分支冷安装引擎选择逻辑确实有差异。
- GitHub `39644675349` 在 Linux ARM64 已完整证明 APK 内 DSH Web 真正启动、HTTP 200、二次进程读取及 ECHILD，**不能自动推断 Android 真机能启动**。

## v177 缩小权限差异而不是取消验证

`IsolatedInstallProcess.start` 将外部进程身份检查拆成：
1. 签名的、由 Java 本次亲自创建的会话启动器自行读 `/proc/self/stat`，核对 PID/PPID/PGID/SID/进程出生时间；超时或自证异常立即失败。
2. Android 主应用若能读子进程 `/proc/<pid>/stat`，则要求完全相同的出生身份。**数据可读却不一致时永远失败，不许进入替代分支。**
3. 若父侧 stat 因权限不可读，尝试 JNI `getsid(pid)`；相符则保持旧有备用证明。
4. 仅在 stat 发生 I/O 权限不可读、`getsid(pid)` 返回 **-EPERM(1) / -EACCES(13)**，且原 Java 进程句柄仍存活时，等待有界检查后采用 `birth` 作为**暂候选**。**这本身没有 START 权限。**
5. 随后的 `NativeTreeControl.accept` 在发送任何 START 指令前，必须验证随机一次性 Unix abstract socket 的内核 `SO_PEERCRED` PID 等于出生 PID、UID 等于当前 App UID、原子进程仍存活，签名协议 READY 匹配，完成持久化的 `beforeLaunch` 记录。任何一步失败都不启动 guest。
6. 控制通道复查使用原 Java Process 句柄持续存活和内核已核实的 peer 身份，不用未核实 PID 发送裸进程组信号；原生监督器仍须回报 `COMMAND_EXITED` 和 `ECHILD` 树空证明。

拒绝的情况：`/proc` 能读却出生时间、父进程、PID 或会话不符、进程退出、`getsid` 返回 ESRCH/无效错误码、真实 SID 不等于出生 SID、SO_PEERCRED PID/UID 不符、控制协议、日志记录前的身份核验不通过。

## 验证工作

- Linux ARM64 原生 DSH Web 实际启动：`39644675349` (v176 源包)
- JVM 安全边界与正反用例：`OwnedBirthEvidenceTest` 在 Standard/Low 两个 flavor 下运行
- **Android/Bionic 实例**：`OwnedBirthAndroidInstrumentation` 在隔离测试 App UID 下直接执行真实签名的 `libdsha-session.so`，要求 NativeTreeControl / peer PID UID / ECHILD 均通过
- macOS Apple Silicon 上 ARM64 Android Emulator：`.github/workflows/android-arm64-emulator-smoke.yml`；它是真 Android 内核用户空间，但也不能代表全部国产 ROM 和 SELinux 策略
- 原版 APK 运行与 v177 的签名、会话迁移尚未在用户手机验证。**不得把模拟器启动成功写成用户手机版启动成功。**

设计约束：不得禁用内核身份验证、跨版本清理用户数据、绕过 APK 签名或恢复独立旧版 DSH 应急包。升级 PR 保持 Draft。
