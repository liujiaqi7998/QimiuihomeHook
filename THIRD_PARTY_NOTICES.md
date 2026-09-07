# 第三方组件

项目自有代码采用 Apache-2.0。下列二进制是经确认的构建依赖，不是原小米桌面程序或反编译产物。

| 文件 | 来源 / 许可 | 用途 |
| --- | --- | --- |
| `mihome-hook/libs/api-82.jar` | [XposedBridge API](https://api.xposed.info/de/robv/android/xposed/api/82/api-82.jar)，Apache-2.0 | compileOnly；LSPosed 在运行时提供实现，不打入模块 APK |
| `mihome-hook/gradle/wrapper/gradle-wrapper.jar` | [Gradle 9.5.1](https://github.com/gradle/gradle/tree/v9.5.1)，Apache-2.0 | 构建引导器，不打入模块 APK |

Xposed 原始版权与第三方声明保存在 `mihome-hook/libs/XPOSED-NOTICE.txt`；完整 Apache-2.0 文本见根目录 LICENSE。Gradle wrapper 的脚本版权头保持不变，附带上游许可与 NOTICE 位于 `mihome-hook/gradle/wrapper/`。

通过 Maven 下载的构建、测试依赖及可能传递的 Kotlin 标准库保留其各自许可。JUnit/Mockito/Byte Buddy 仅用于主机测试，不打入模块 APK。发布二进制时应同时保留构建所含依赖要求的许可说明。

小米、MIUI、HyperOS 和 LSPosed 的名称仅用于兼容性说明，其商标与原厂程序权利属于各自权利人。本仓库不提供厂商 APK 或其反编译实现。
