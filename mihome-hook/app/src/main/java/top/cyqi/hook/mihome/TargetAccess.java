package top.cyqi.hook.mihome;

import android.graphics.ColorFilter;
import android.graphics.LightingColorFilter;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;

/** Exact descriptors documented in docs/ARCHITECTURE.md; no name-only hook resolution. */
final class TargetAccess implements FilterCallback.Access {
  final Method target;
  private final Field flags;
  private final Method config, isStub, singleton, disabled, progress;

  private TargetAccess(ClassLoader loader) throws Exception {
    Class<?> shortcut = load(loader, "com.miui.home.launcher.ShortcutInfo");
    Class<?> item = load(loader, "com.miui.home.model.api.ItemInfoWithIconAndMessage");
    Class<?> stub = load(loader, "com.miui.home.launcher.SystemAppStubConfig");
    Class<?> filter = load(loader, "com.miui.home.launcher.common.IconDisabledFilter");
    Class<?> utils = load(loader, "com.miui.home.common.utils.ProgressIconUtils");
    if (!item.isAssignableFrom(shortcut)) throw new NoSuchFieldException("unexpected hierarchy");
    target = exact(shortcut, "getColorFilter", ColorFilter.class, false);
    config = exact(shortcut, "getSystemApplicationConfig", stub, false);
    isStub = exact(stub, "isMiuiAppStub", boolean.class, false);
    singleton = exact(filter, "getInstance", filter, true);
    disabled = exact(filter, "getDisabledColorFilter", ColorFilter.class, false);
    progress = exact(utils, "getProgressFilter", LightingColorFilter.class, true);
    flags = item.getDeclaredField("runtimeStatusFlags");
    if (flags.getType() != int.class
        || Modifier.isStatic(flags.getModifiers())
        || !Modifier.isPublic(flags.getModifiers()))
      throw new NoSuchFieldException("flags descriptor");
  }

  static TargetAccess resolve(ClassLoader loader) throws Exception {
    return new TargetAccess(loader);
  }

  private static Class<?> load(ClassLoader loader, String name) throws ClassNotFoundException {
    return Class.forName(name, false, loader);
  }

  static Method exact(
      Class<?> owner, String name, Class<?> result, boolean isStatic, Class<?>... parameters)
      throws NoSuchMethodException {
    Method method = owner.getDeclaredMethod(name, parameters);
    if (method.getReturnType() != result
        || Modifier.isStatic(method.getModifiers()) != isStatic
        || !Modifier.isPublic(method.getModifiers())
        || Modifier.isAbstract(method.getModifiers())) {
      throw new NoSuchMethodException(owner.getName() + "." + name + " descriptor mismatch");
    }
    return method;
  }

  public int flags(Object receiver) throws Exception {
    return flags.getInt(receiver);
  }

  public Object disabledFilter() throws Exception {
    return disabled.invoke(singleton.invoke(null));
  }

  public Object normalFilter(Object receiver) throws Exception {
    Object value = config.invoke(receiver);
    return value != null && (Boolean) isStub.invoke(value) ? progress.invoke(null) : null;
  }
}
