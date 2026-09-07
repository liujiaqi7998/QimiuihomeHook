package top.cyqi.hook.mihome;

import static org.junit.Assert.*;

import org.junit.Test;

public class FilterCallbackTest {
  @Test
  public void removesOnlySuspensionForEveryDisabledCombination() {
    Object disabled = new Object();
    for (int high : new int[] {0, 64, 128, 0x40000000, 0xffffffc0}) {
      for (int low = 0; low < 64; low++) {
        Frame frame = new Frame(disabled);
        new FilterCallback(new Access(high | low, disabled)).after(frame);
        assertSame("mask=" + (high | low), low == 4 ? null : disabled, frame.result);
        assertEquals(low == 4 ? 1 : 0, frame.writes);
      }
    }
  }

  @Test
  public void preservesThrowableAndForeignFilter() {
    Object disabled = new Object();
    Object foreign = new Object();
    Frame failed = new Frame(disabled);
    failed.error = new IllegalStateException("original");
    new FilterCallback(new Access(4, disabled)).after(failed);
    assertSame(disabled, failed.result);
    assertEquals(0, failed.writes);
    assertEquals("original", failed.error.getMessage());
    Frame other = new Frame(foreign);
    new FilterCallback(new Access(4, disabled)).after(other);
    assertSame(foreign, other.result);
    assertEquals(0, other.writes);
  }

  @Test
  public void restoresStubProgressOnlyForKnownDisabledFilter() {
    Object disabled = new Object(), progress = new Object();
    Access stub =
        new Access(4, disabled) {
          @Override
          public Object normalFilter(Object o) {
            return progress;
          }
        };
    Frame f = new Frame(disabled);
    new FilterCallback(stub).after(f);
    assertSame(progress, f.result);
  }

  @Test
  public void nullOriginalDoesNotWriteOrLookup() {
    final int[] reads = {0};
    Access a =
        new Access(4, new Object()) {
          @Override
          public int flags(Object o) {
            reads[0]++;
            return 4;
          }

          @Override
          public Object disabledFilter() {
            reads[0]++;
            return disabled;
          }

          @Override
          public Object normalFilter(Object o) {
            reads[0]++;
            return new Object();
          }
        };
    Frame f = new Frame(null);
    new FilterCallback(a).after(f);
    assertNull(f.result);
    assertEquals(0, f.writes);
    assertEquals(0, reads[0]);
  }

  @Test
  public void reflectiveFailuresLeaveResultUnwritten() {
    Object disabled = new Object();
    for (int stage = 0; stage < 3; stage++) {
      final int failure = stage;
      Access broken =
          new Access(4, disabled) {
            @Override
            public int flags(Object o) throws Exception {
              if (failure == 0) throw new IllegalAccessException();
              return 4;
            }

            @Override
            public Object disabledFilter() throws Exception {
              if (failure == 1) throw new IllegalAccessException();
              return disabled;
            }

            @Override
            public Object normalFilter(Object o) {
              throw new NoClassDefFoundError("missing");
            }
          };
      Frame f = new Frame(disabled);
      new FilterCallback(broken).after(f);
      assertSame(disabled, f.result);
      assertEquals(0, f.writes);
    }
  }

  @Test
  public void callbackEmitsFirstHitAndBoundedFailures() {
    java.util.List<String> events = new java.util.ArrayList<>();
    BoundedLog log = new BoundedLog(events::add);
    Object disabled = new Object();
    FilterCallback ok = new FilterCallback(new Access(4, disabled), log);
    for (int n = 0; n < 10; n++) ok.after(new Frame(disabled));
    assertEquals(1, events.size());
    assertTrue(events.get(0).endsWith("HIT"));
    FilterCallback broken =
        new FilterCallback(
            new Access(4, disabled) {
              public Object normalFilter(Object o) {
                throw new LinkageError();
              }
            },
            log);
    for (int n = 0; n < 10; n++) broken.after(new Frame(disabled));
    assertEquals(4, events.size());
    assertTrue(events.get(3).endsWith("ERROR"));
  }

  static class Frame implements FilterCallback.Frame {
    Object result;
    Throwable error;
    int writes;

    Frame(Object value) {
      result = value;
    }

    public Object receiver() {
      return this;
    }

    public Object result() {
      return result;
    }

    public boolean hasThrowable() {
      return error != null;
    }

    public void replace(Object value) {
      result = value;
      writes++;
    }
  }

  static class Access implements FilterCallback.Access {
    int flags;
    Object disabled;

    Access(int f, Object d) {
      flags = f;
      disabled = d;
    }

    public int flags(Object o) throws Exception {
      return flags;
    }

    public Object disabledFilter() throws Exception {
      return disabled;
    }

    public Object normalFilter(Object o) throws Exception {
      return null;
    }
  }
}
