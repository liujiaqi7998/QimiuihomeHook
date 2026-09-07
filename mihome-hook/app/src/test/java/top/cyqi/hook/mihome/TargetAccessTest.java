package top.cyqi.hook.mihome;

import static org.junit.Assert.*;

import com.miui.home.common.utils.ProgressIconUtils;
import com.miui.home.launcher.*;
import com.miui.home.launcher.common.IconDisabledFilter;
import org.junit.Test;

public class TargetAccessTest {
  @Test
  public void rejectsWrongStaticnessReturnArgumentsAndMissingClass() throws Exception {
    for (int variant = 0; variant < 4; variant++) {
      try {
        switch (variant) {
          case 0:
            TargetAccess.exact(
                ShortcutInfo.class, "getColorFilter", android.graphics.ColorFilter.class, true);
            break;
          case 1:
            TargetAccess.exact(
                ProgressIconUtils.class,
                "getProgressFilter",
                android.graphics.ColorFilter.class,
                true);
            break;
          case 2:
            TargetAccess.exact(
                ShortcutInfo.class,
                "getColorFilter",
                android.graphics.ColorFilter.class,
                false,
                int.class);
            break;
          default:
            TargetAccess.resolve(new ClassLoader(null) {});
        }
        fail("descriptor mismatch accepted");
      } catch (ReflectiveOperationException expected) {
      }
    }
  }

  @Test
  public void exactTargetReflectionDrivesAfterCallback() throws Exception {
    TargetAccess a;
    try {
      a = TargetAccess.resolve(getClass().getClassLoader());
    } catch (Exception e) {
      throw new AssertionError("valid target descriptors must resolve", e);
    }
    assertEquals("getColorFilter", a.target.getName());
    ShortcutInfo info = new ShortcutInfo();
    info.runtimeStatusFlags = 4;
    FilterCallbackTest.Frame f =
        new FilterCallbackTest.Frame(IconDisabledFilter.filter) {
          public Object receiver() {
            return info;
          }
        };
    new FilterCallback(a).after(f);
    assertNull(f.result);
    assertEquals(1, f.writes);
    info.config = new SystemAppStubConfig();
    info.config.stub = true;
    f.result = IconDisabledFilter.filter;
    new FilterCallback(a).after(f);
    assertSame(ProgressIconUtils.filter, f.result);
    assertEquals(4, info.runtimeStatusFlags);
    info.config.stub = false;
    assertNull(a.normalFilter(info));
  }
}
