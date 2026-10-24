工作界面调整与文件搜索修复（Standard 验证版）。

- 模型选择保留原模型目录、搜索和保存流程。思考强度使用当前模型提供的档位，最高档有紫色像素动效；切换模型与说明时，面板和滑条位置稳定。
- 缓存命中率、累计用量、活动与速度、上下文环全部可见，并分别保留详情。回复后的按钮和完成状态保留。
- 修正软件把自身必需的运行组件误判成异常，连查看目录都被阻止的问题；额外未知组件、删除和覆盖等原有确认规则保留。
- 手机文件搜索改用兼容的固定版本；同时修正搜索程序已退出、软件却一直等它结束的问题。
- 网页获取失败增加具体原因错误码。现有截图不足以确认其网络原因，此项是诊断改善。
- 保留普通关闭重开、自动小窗默认关闭和独立启动日志页，继续使用 v180 起固定签名。

[本次完整构建、Android 检查、ARM64 搜索与固定签名](https://github.com/poteeto/workspace1/actions/runs/40114939008)全部通过。Standard / Low 各 1720 项单元检查，0 失败；Release Lint 无错误。

此为 Standard 非调试签名验证版。未在原 realme Android 16 手机验收；ARM64 Linux 和 Android 模拟器检查不等于该手机完整使用验收。网页获取失败的原始网络原因仍未确定。

附件提供 APK、SHA256 和 verification.json。[源码与验证范围](https://github.com/poteeto/workspace1/blob/upgrade/dsh-0.2.1-rc.2/docs/releases/v0.2.34-build184-workspace.md)。

APK SHA256：`09707f1e1e5b293ef862e298fbc0446b034d647fc11f3b1b56b796cb2e8a4d33`
