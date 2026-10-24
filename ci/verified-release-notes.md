默认不再自动弹小窗，首页不再展开启动日志。

- “离开应用时自动进入小窗”默认关闭，旧版覆盖升级也默认关闭。需要时在“设置 → 运行与显示”主动开启，立即生效。
- 首页点“启动日志”进入独立页面，支持实时查看、上翻阅读、下载，以及进入历史记录与诊断；安全启动、恢复和访问地址入口保留。
- 保留 v182 普通关闭重开修复，继续使用 v180 起相同固定签名，可覆盖 v180–v182。

此为 Standard 非调试签名验证版。Android 模拟器检查使用静态 debug 页面测试真实小窗宿主，布局检查不安装 Ubuntu；尚未连接原 realme Android 16 手机，不声明真机或完整聊天验收。

附件：签名 APK、SHA256、verification.json。[检查结果、源码及验证范围](https://github.com/poteeto/workspace1/blob/upgrade/dsh-0.2.1-rc.2/docs/releases/v0.2.33-build183-ui.md)。

[完整 GitHub 构建与签名](https://github.com/poteeto/workspace1/actions/runs/39977822726)通过。Standard / Low 各 1720 项单元检查，0 失败、各 3 项跳过；Release Lint 无错误。Android 小窗与日志 19 项行为、中英文页面及三轮重开检查通过。

安装包 SHA256：`e52a958bd926a1ac0f9c596ac74dbbe5658a2ba20c8b7e18a093abb92b89b73d`
