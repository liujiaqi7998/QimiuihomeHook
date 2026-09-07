package top.cyqi.hook.mihome;

import android.app.Application;
import android.content.Context;

import de.robv.android.xposed.IXposedHookLoadPackage;
import de.robv.android.xposed.XC_MethodHook;
import de.robv.android.xposed.XposedBridge;
import de.robv.android.xposed.callbacks.XC_LoadPackage.LoadPackageParam;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.concurrent.atomic.AtomicBoolean;

/** A process-local lifecycle observer and one narrowly scoped rendering after-hook. */
public final class MainHook implements IXposedHookLoadPackage {
  private final AtomicBoolean observed = new AtomicBoolean();
  private final Activation activation = new Activation();
  private final BoundedLog log = new BoundedLog(XposedBridge::log);

  @Override
  public void handleLoadPackage(LoadPackageParam load) {
    if (load == null
        || !Activation.acceptsProcess(load.packageName, load.processName)
        || !observed.compareAndSet(false, true)) return;
    try {
      Method attach = Application.class.getDeclaredMethod("attach", Context.class);
      if (attach.getReturnType() != void.class
          || Modifier.isStatic(attach.getModifiers())
          || Modifier.isAbstract(attach.getModifiers())) {
        log.emit(BoundedLog.Event.ERROR);
        return;
      }
      XposedBridge.hookMethod(
          attach,
          new XC_MethodHook() {
            @Override
            protected void afterHookedMethod(MethodHookParam param) {
              if (param.hasThrowable()) return;
              try {
                Context context = (Context) param.args[0];
                if (!Activation.PACKAGE.equals(context.getPackageName())) return;

                boolean installed =
                    activation.activate(
                        load.packageName,
                        load.processName,
                        () -> install(load.classLoader));
                log.emit(installed ? BoundedLog.Event.INSTALLED : BoundedLog.Event.SKIPPED);
              } catch (Throwable ignored) {
                log.emit(BoundedLog.Event.ERROR);
              }
            }
          });
      log.emit(BoundedLog.Event.WAITING);
    } catch (Throwable ignored) {
      log.emit(BoundedLog.Event.ERROR);
    }
  }

  private void install(ClassLoader loader) throws Exception {
    TargetAccess access = TargetAccess.resolve(loader); // Resolve everything before hooking.
    FilterCallback core = new FilterCallback(access, log);
    XposedBridge.hookMethod(
        access.target,
        new XC_MethodHook() {
          @Override
          protected void afterHookedMethod(MethodHookParam param) {
            dispatch(param, core);
          }
        });
  }

  static void dispatch(XC_MethodHook.MethodHookParam param, FilterCallback core) {
    core.after(
        new FilterCallback.Frame() {
          public Object receiver() {
            return param.thisObject;
          }

          public Object result() {
            return param.getResult();
          }

          public boolean hasThrowable() {
            return param.hasThrowable();
          }

          public void replace(Object value) {
            param.setResult(value);
          }
        });
  }
}
