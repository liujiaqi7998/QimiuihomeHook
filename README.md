# QimiuihomeHook

让被挂起的应用在小米系统桌面中保持彩色图标的 LSPosed 模块。

> **只修改桌面滤镜，不解除应用挂起，不绕过系统的启动限制。** 项目与 Xiaomi、MIUI、HyperOS 或 LSPosed 官方无隶属关系。

## 功能与边界

- 模块包名：`top.cyqi.hook.mihome`。
- 推荐作用域：**仅 `com.miui.home`（系统桌面）**，代码只在其同名主进程工作。
- 不再限制桌面版本号：对所有版本尝试解析所需接口，接口不匹配时保留原行为。
- 仅取消“挂起”这一禁用原因产生的图标滤镜；工作资料暂停等其他禁用原因仍保留。
- 保留 MIUI 安装占位图标的正常进度滤镜，不覆盖其他模块返回的空滤镜或不同滤镜。
- 无启动界面、设置页、网络权限、统计收集或 Toast。

**“不限制版本号”不等于“所有版本均已验证兼容”。** 当前实现依赖特定类/字段/方法结构，以及挂起标志 `4`、禁用掩码 `0x3f` 的语义。反射预检能发现接口变化，但不能识别所有“签名不变、语义改变”的情况。不同桌面版本、主题、动态图标、ART 优化或其他 Hook 模块可能影响效果。发现不兼容时请停用模块，不要清除桌面数据。

## 环境要求

- Android 14 或更高版本（模块 `minSdk 34`）。取消桌面版本号限制并不降低 Android 最低版本。
- 已正常工作的、支持传统 Xposed API 82 的 LSPosed 环境。
- 使用 `com.miui.home` 作为系统桌面。

## 安装和使用

1. 从 [GitHub Releases](https://github.com/liujiaqi7998/QimiuihomeHook/releases) 下载正式签名 APK，或自行构建下面的 Debug APK。Git 历史不提交 APK 或签名密钥；Release 附带文件校验和与签名指纹。
2. 安装模块，在 LSPosed 中启用，并确认作用域只勾选“系统桌面”。推荐作用域不会覆盖管理器中已有的历史选择。
3. 重启桌面进程或重启设备，使已缓存的图标重新绑定。不要清除桌面数据。
4. 对一个可安全测试的普通应用执行挂起：其图标应保持彩色，但启动仍受到系统限制。`pm suspend` 是挂起，`pm unsuspend` 是解除挂起。
5. 解除挂起后检查启动恢复，并回归桌面、抽屉及文件夹图标。

回滚：在 LSPosed 停用模块或移除其作用域，再重启桌面。模块不改变应用真实挂起状态，不需要清除桌面数据。

## 构建

工程位于 `mihome-hook/`。使用 Gradle Wrapper，无需全局安装 Gradle。

工具链：Gradle 9.5.1、Android Gradle Plugin 9.2.1、SDK platform 35；Java 编译目标 17。当前主机验证使用 JDK 26，建议先使用相同工具链复现构建。设置 `JAVA_HOME` 与 `ANDROID_HOME` 指向自己的 JDK/SDK；不要提交 `local.properties`。

```sh
git clone git@github.com:liujiaqi7998/QimiuihomeHook.git
cd QimiuihomeHook/mihome-hook
./gradlew --console=plain clean :app:testDebugUnitTest :app:lint :app:assembleDebug :app:assembleRelease
```

Windows PowerShell / cmd 使用 `gradlew.bat`：

```powershell
cd QimiuihomeHook\mihome-hook
.\gradlew.bat --console=plain clean :app:testDebugUnitTest :app:lint :app:assembleDebug :app:assembleRelease
```

首次构建需要下载 Gradle/Google Maven/Maven Central 依赖；官方 Xposed API 82 以 compile-only JAR 随源码提供，来源与许可证见 [第三方说明](THIRD_PARTY_NOTICES.md)。

| 产物 | 用途 |
| --- | --- |
| `app/build/outputs/apk/debug/app-debug.apk` | Android Debug 证书签名，可用于安装测试 |
| `app/build/outputs/apk/release/app-release-unsigned.apk` | 未签名，不能直接安装；发行前需使用自己保管的密钥签名 |

Debug 证书不是生产身份保证；换机器构建时签名通常不同，可能无法直接覆盖更新。不要上传 debug keystore、生产密钥或带凭据的 Gradle 配置。

正式 Release 使用项目独立且固定的发布密钥签名，公钥证书指纹固定在 `ci/release-certificate.sha256`。此前安装的 Debug 包与正式版签名不同：请先在 LSPosed 停用模块、卸载 Debug 包，再安装 Release 并重新启用作用域；之后正式版本之间使用同一签名，可正常覆盖升级。

## CI 与自动发布

- 普通 main 提交、Pull Request 和手动触发运行 CI：校验构建依赖、运行测试/Lint、构建 APK。
- 推送 `vX.Y.Z` 标签触发 Release 流程；标签必须匹配构建得到的版本名称，提交必须来自 main 历史。
- 发布流程通过质量门禁后，才在独立发布任务中使用 GitHub Actions Secrets 签名。PR 和普通 CI 不使用发布密钥。
- APK 签名指纹、版本和对齐检查通过后创建草稿 Release；附件上传并下载回读校验成功才转为正式发布。已发布版本不会被自动覆盖。
- 下载附件包括 APK、`SHA256SUMS` 和 `SIGNING-CERTIFICATE.txt`。自动发布成功不等于通过真机兼容性验证。

维护者配置、签名备份和发布操作见 [发布指南](docs/RELEASING.md)。

## 验证状态

提供 JVM 单元测试，覆盖禁用位组合、异常/null/外来滤镜保护、stub 进度恢复、接口预检、包名/主进程门控、一次安装和日志预算。测试会运行实际决策、反射代码和 callback adapter；Android 图形类型与 Xposed 外部参数使用测试替身，**并不执行真实 LSPosed native 桥或验证屏幕像素**。

- 单测报告：`app/build/reports/tests/testDebugUnitTest/index.html`
- Lint 报告：`app/build/reports/lint-results-debug.html`
- Lint 保留全部规则，可能报告私有 `Application.attach` 反射、SDK/依赖版本、无图标或备份规则等警告。
- JDK 26 下 Mockito/Byte Buddy 使用仅限测试 JVM 的兼容参数，可能输出弃用提示。

主机构建与 APK 静态检查不替代真机验收。目前不声称已完成多版本 HyperOS/LSPosed 真机验证。完整回归清单见 [贡献指南](CONTRIBUTING.md)。

## 隐私

模块不请求权限、不访问网络、不采集或上传应用列表、设备标识和使用记录。仅向本机 LSPosed 日志写入固定事件：`[MiHomeColor] WAITING / INSTALLED / SKIPPED / HIT / ERROR`；普通事件各最多一次，错误最多三次。分享日志前仍需自行脱敏，因为 LSPosed 的其他日志可能含私人信息。

原桌面 APK、反编译输出、设备资料、本机构建日志、私有分析笔记、签名材料和旧源码打包件不进入 Git。Git 提交使用公开账号的 noreply 身份。

## 源码导航

- [模块工程](mihome-hook/)
- [架构与兼容策略](mihome-hook/docs/ARCHITECTURE.md)
- [贡献指南](CONTRIBUTING.md)
- [安全问题报告](SECURITY.md)
- [更新日志](CHANGELOG.md)

## 许可证

本项目采用 [Apache License 2.0](LICENSE)。第三方组件保留各自的版权和许可；不包含或授权分发小米桌面 APK、反编译代码或商标资源。
