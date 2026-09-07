# Xposed 编译 API

`api-82.jar` 来自 [官方发布路径](https://api.xposed.info/de/robv/android/xposed/api/82/api-82.jar)，未经修改。

SHA-256：`f48c635f1c7469fdec0e00ad2ea0b7a6b2f5b55065784a35b7ca3a84615e8e25`。

许可证为 Apache-2.0；版权与上游 NOTICE 见同目录 `XPOSED-NOTICE.txt`，完整许可证见仓库根目录 LICENSE。

此 JAR 的方法体是官方编译 stub，不是可执行的 Xposed 框架。生产只使用 compileOnly；JVM 测试使用同一 API 类型和 Mockito 外部参数替身，运行实际 adapter/策略。禁止手写不准确的 API 替代品；尤其 hookMethod 描述符必须是 `(Member, XC_MethodHook) -> XC_MethodHook.Unhook`。API 实现不应出现在最终 APK 中。
