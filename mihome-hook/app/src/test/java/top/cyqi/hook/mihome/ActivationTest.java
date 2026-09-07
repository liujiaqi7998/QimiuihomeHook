package top.cyqi.hook.mihome;

import static org.junit.Assert.*;

import org.junit.Test;

public class ActivationTest {
  @Test
  public void activationRequiresNoVersionMetadata() throws Exception {
    int[] installs = {0};
    assertTrue(new Activation().activate(
        "com.miui.home", "com.miui.home", () -> installs[0]++));
    assertEquals(1, installs[0]);
    // The activation contract accepts no version name or numeric version code.
    assertNotNull(Activation.class.getDeclaredMethod(
        "activate", String.class, String.class, Activation.Install.class));
    for (java.lang.reflect.Method method : Activation.class.getDeclaredMethods()) {
      if (method.getName().equals("activate")) assertEquals(3, method.getParameterCount());
    }
  }

  @Test
  public void exactPackageAndMainProcessInstallOnlyOnce() throws Exception {
    Activation a = new Activation();
    int[] installs = {0};
    Activation.Install install = () -> installs[0]++;
    assertFalse(a.activate("other", "com.miui.home", install));
    assertFalse(a.activate("com.miui.home", "com.miui.home:remote", install));
    assertFalse(a.activate(null, "com.miui.home", install));
    assertFalse(a.activate("com.miui.home", null, install));
    assertEquals(0, installs[0]);
    assertTrue(a.activate("com.miui.home", "com.miui.home", install));
    assertFalse(a.activate("com.miui.home", "com.miui.home", install));
    assertEquals(1, installs[0]);
    assertTrue(Activation.acceptsProcess("com.miui.home", "com.miui.home"));
    assertFalse(Activation.acceptsProcess(null, null));
  }

  @Test
  public void failedInstallationIsNotRepeated() throws Exception {
    Activation a = new Activation();
    int[] n = {0};
    try {
      a.activate(
          "com.miui.home",
          "com.miui.home",
          () -> {
            n[0]++;
            throw new Exception("preflight");
          });
      fail();
    } catch (Exception expected) {
      assertEquals("preflight", expected.getMessage());
    }
    assertFalse(a.activate("com.miui.home", "com.miui.home", () -> n[0]++));
    assertEquals(1, n[0]);
  }
}
