# 模块工程

本目录包含 `top.cyqi.hook.mihome` 的 Android/LSPosed 工程。

使用说明、构建命令、兼容边界、隐私与许可证请阅读 [项目 README](../README.md)。实现原理见 [架构说明](docs/ARCHITECTURE.md)。

```sh
./gradlew --console=plain :app:testDebugUnitTest :app:lint :app:assembleDebug :app:assembleRelease
```

Windows 使用 `gradlew.bat`。本工程不限制系统桌面版本号，但仅在 `com.miui.home` 主进程内通过反射预检后安装渲染 Hook；不保证所有版本均兼容。
