package top.cyqi.hook.mihome;

import static org.junit.Assert.*;
import static org.mockito.Mockito.*;

import de.robv.android.xposed.IXposedHookLoadPackage;
import de.robv.android.xposed.XC_MethodHook.MethodHookParam;
import java.lang.reflect.Method;
import org.junit.Test;

public class XposedBoundaryTest {
  @Test
  public void officialApiHasRuntimeHookMethodAbi() throws Exception {
    Method hook =
        de.robv.android.xposed.XposedBridge.class.getDeclaredMethod(
            "hookMethod",
            java.lang.reflect.Member.class,
            de.robv.android.xposed.XC_MethodHook.class);
    assertEquals("de.robv.android.xposed.XC_MethodHook$Unhook", hook.getReturnType().getName());
    assertTrue(java.lang.reflect.Modifier.isStatic(hook.getModifiers()));
  }

  @Test
  public void wrongPackageOrProcessNeverTouchesXposed() {
    MainHook main = new MainHook();
    main.handleLoadPackage(null);
    de.robv.android.xposed.callbacks.XC_LoadPackage.LoadPackageParam load =
        mock(de.robv.android.xposed.callbacks.XC_LoadPackage.LoadPackageParam.class);
    load.packageName = "other";
    load.processName = "com.miui.home";
    main.handleLoadPackage(load);
    load.packageName = "com.miui.home";
    load.processName = "com.miui.home:remote";
    main.handleLoadPackage(load);
  }

  @Test
  public void realAdapterWritesOnlySuccessfulVerifiedResult() throws Exception {
    Class<?> type;
    try {
      type = Class.forName("top.cyqi.hook.mihome.MainHook");
    } catch (ClassNotFoundException e) {
      throw new AssertionError("Xposed entrypoint missing", e);
    }
    assertTrue(IXposedHookLoadPackage.class.isAssignableFrom(type));
    Method dispatch =
        type.getDeclaredMethod("dispatch", MethodHookParam.class, FilterCallback.class);
    Object disabled = new Object();
    FilterCallback core = new FilterCallback(new FilterCallbackTest.Access(4, disabled));
    MethodHookParam param = mock(MethodHookParam.class);
    when(param.getResult()).thenReturn(disabled);
    dispatch.invoke(null, param, core);
    verify(param).setResult(null);
    MethodHookParam failed = mock(MethodHookParam.class);
    when(failed.hasThrowable()).thenReturn(true);
    dispatch.invoke(null, failed, core);
    verify(failed, never()).setResult(any());
    verify(failed, never()).setThrowable(any());
    MethodHookParam foreign = mock(MethodHookParam.class);
    when(foreign.getResult()).thenReturn(new Object());
    dispatch.invoke(null, foreign, core);
    verify(foreign, never()).setResult(any());
  }
}
