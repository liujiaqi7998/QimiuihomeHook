# 自动构建与 Release 发布

## 触发条件

- main 提交、Pull Request 或手动触发：运行只读 CI，检查构建依赖、测试、Lint 和 APK 构建。
- 推送 `vX.Y.Z` 标签：独立 Release 工作流先通过质量门禁，再签名与发布。
- 标签版本必须等于 `mihome-hook/app/build.gradle` 的 `versionName`；`versionCode` 应随版本递增，提交必须位于 main 历史中。

本地 Release 构建默认仍是未签名 APK。正式签名只在发布任务中进行，不为普通 PR 或 main CI 提供发布密钥。

## 一次性签名配置

在 GitHub 仓库 Settings → Secrets and variables → Actions 配置以下 repository secrets：

| Secret | 内容 |
| --- | --- |
| `ANDROID_KEYSTORE_BASE64` | 项目专用 PKCS12 keystore 的 Base64 编码；不是源码文件 |
| `ANDROID_KEYSTORE_PASSWORD` | keystore 密码 |
| `ANDROID_KEY_ALIAS` | 密钥别名 |
| `ANDROID_KEY_PASSWORD` | 私钥密码 |

公开的预期证书 SHA-256 放在 `ci/release-certificate.sha256`。发布脚本必须将实际签名指纹与其比对；缺少配置或不匹配时失败，绝不自动改用 Debug 或临时密钥。

`GITHUB_TOKEN` 由 Actions 自动提供，不需要另存一个长期个人访问令牌。只有发布任务请求 `contents: write`，构建任务与 PR 保持只读。Actions 版本固定到完整提交 SHA，Gradle wrapper 和 API JAR 另作哈希校验。

## 密钥备份

维护者必须在仓库外妥善备份 keystore、密码、别名和公开证书，建议使用加密离线副本。GitHub Secrets 的明文值设置后不能作为可下载备份。不要提交这些内容，也不要将 Base64、密码或完整本地配置粘贴到 Issue、构建日志或 Release 附件。

丢失发布私钥意味着无法给已安装版本提供同签名更新。不要为了通过构建而删除证书指纹检查。签名迁移必须明确评估 Android 的更新身份和用户迁移方式。

Fork 不会继承原仓库 secrets。维护者应使用自己的签名材料和指纹；相同包名、不同签名的 APK 不能直接覆盖安装。

## 发布步骤

1. 更新模块 `versionName` / `versionCode` 和 CHANGELOG，完成代码审查。
2. 推送 main 并确认 CI 通过。
3. 给同一已验证提交创建标签并推送，例如：

```sh
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0
```

后续版本替换示例版本号，不要移动已经发布的标签。

4. 在 Actions 中观察 Release：测试/Lint/构建 → 签名与校验 → 草稿 Release → 附件上传 → 下载回读校验 → 正式发布。
5. 发布后核对 APK、SHA256SUMS、SIGNING-CERTIFICATE.txt，以及 Release 标签所指向的提交。

已正式发布的版本不会被自动覆盖。失败留下草稿时，可排除故障后重跑；不要通过移动标签掩盖构建或签名问题。

## 下载与验签

`SHA256SUMS` 用于检测下载文件是否损坏；证书指纹用于识别签名身份。它们都不等同于设备上的运行效果验证。

使用 Android SDK 的工具检查 APK：

```sh
apksigner verify --verbose --print-certs top.cyqi.hook.mihome-1.1.0.apk
```

输出的证书 SHA-256 应与仓库固定指纹及 Release 的 SIGNING-CERTIFICATE.txt 一致。Linux/macOS 可用 `sha256sum -c SHA256SUMS`（或等价 SHA-256 工具）核对文件摘要。

首次从旧 Debug 包切换到正式发布包时，签名不同：先停用模块并卸载 Debug 包，再安装 Release，重新勾选系统桌面作用域并重启桌面。正式版本之间沿用同一个签名，可覆盖更新。

## 仍需真机验证

CI 验证构建、静态结构与签名，不执行真实 LSPosed native 桥，也不证明所有桌面版本、主题或动态图标都兼容。真机回归和回滚步骤见根目录 README 与 CONTRIBUTING.md。
