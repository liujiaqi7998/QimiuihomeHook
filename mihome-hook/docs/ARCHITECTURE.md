# 架构与兼容策略

## 调用链

模块拦截模型层 `com.miui.home.launcher.ShortcutInfo.getColorFilter(): ColorFilter`，而非全局拦截 `ImageView` 或 `Drawable`。

已分析的结构中，主图标组件 `ShortcutIcon` 继承 TextView；模型同步/异步图标加载会将该 getter 的结果应用到 Drawable。应用抽屉与 1×1、2×2 文件夹预览也消费此模型滤镜。这说明一个模型入口可覆盖这些路径，不能据此保证所有主题或未来实现都使用相同路径。

## 加载与预检

1. `MainHook` 仅接受包名和进程名均为 `com.miui.home` 的回调。
2. 在 `Application.attach(Context)` 成功后，确认上下文包名，再尝试一次性安装。没有版本名称或版本数字白名单。
3. `TargetAccess` 校验以下反射接口的精确返回类型、参数、static/instance、public 属性和模型继承关系。任何不匹配均不安装渲染 Hook。

| 所属类 | 成员 | 约定 |
| --- | --- | --- |
| `launcher.ShortcutInfo` | `getColorFilter()` | 实例方法，返回 `android.graphics.ColorFilter` |
| `model.api.ItemInfoWithIconAndMessage` | `runtimeStatusFlags` | public int 实例字段 |
| `launcher.ShortcutInfo` | `getSystemApplicationConfig()` | 返回 `launcher.SystemAppStubConfig` |
| `launcher.SystemAppStubConfig` | `isMiuiAppStub()` | 实例方法，返回 boolean |
| `launcher.common.IconDisabledFilter` | `getInstance()` | 静态，返回本类型 |
| `launcher.common.IconDisabledFilter` | `getDisabledColorFilter()` | 实例方法，返回 ColorFilter |
| `common.utils.ProgressIconUtils` | `getProgressFilter()` | 静态，精确返回 LightingColorFilter |

表中短类名均位于 `com.miui.home` 下。当前反射结构源自实际 APK 的接口分析，未把厂商源码或 DEX 纳入仓库。测试中的同名类是最小行为夹具，不能当成厂商实现。

## 结果修改策略

渲染 Hook 只有 after 回调，不手动重新调用原方法：

1. 原调用抛出异常或返回 null：保持原样。
2. 仅当 `(runtimeStatusFlags & 0x3f) == 4`，即低六位禁用原因只有挂起时继续。
3. 原结果必须与已知禁用滤镜为同一对象（`==`），不使用 equals，不清除未知滤镜。
4. 在所有查询成功后只写一次返回值：普通图标为 null；MIUI stub 为正常的进度滤镜。
5. 反射失败时保持原结果。不会为了恢复 stub 而在失败时强行返回 null。

`IconDisabledFilter.getInstance()` 在已分析实现中还会设置 DISABLED 状态，并非绝对无副作用。因此先通过异常、非空和标志位检查，才进行身份确认；不在启动时全局预热、不直接改写单例缓存。

## 不改变的行为

不修改 PackageManager、ApplicationInfo、runtimeStatusFlags、isDisabled、真实挂起状态或启动限制；混合禁用位仍保持禁用滤镜。不会全局移除灰度/亮度矩阵，也不会覆盖其他模块已清除或替换的滤镜。

## 跨版本限制

“所有版本尝试匹配”只是取消版本号拒绝。Android 最低版本仍是 14。类重命名、签名改变会触发安全跳过；如果状态位语义改变但接口未变，反射预检无法自动识别。后续 Hook 的覆写、ART 优化和主题专用路径也可能改变最终结果。

适配新结构时应加入明确的适配器、证据和回归测试，不用宽泛的全局 Hook 猜测，也不要为了增加命中率改写模型或系统状态。

## 日志与失败

固定日志最多七条/进程，不带应用列表或堆栈。`WAITING` 为生命周期 observer 已安装，`INSTALLED` 为渲染 Hook 已注册，`SKIPPED` 为门控拒绝/重复尝试，`HIT` 为首次替换，`ERROR` 为安全回退。接口不匹配可能只看到 ERROR；这些事件不是屏幕显示成功的证明。
