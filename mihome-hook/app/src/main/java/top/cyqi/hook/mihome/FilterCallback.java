package top.cyqi.hook.mihome;

/** Runs after the original method. All lookups complete before the single result write. */
final class FilterCallback {
  interface Frame {
    Object receiver();

    Object result();

    boolean hasThrowable();

    void replace(Object value);
  }

  interface Access {
    int flags(Object receiver) throws Exception;

    Object disabledFilter() throws Exception;

    Object normalFilter(Object receiver) throws Exception;
  }

  private final Access access;
  private final BoundedLog log;

  FilterCallback(Access access) {
    this(access, new BoundedLog(message -> {}));
  }

  FilterCallback(Access access, BoundedLog log) {
    this.access = access;
    this.log = log;
  }

  void after(Frame frame) {
    try {
      if (frame.hasThrowable()) return;
      Object original = frame.result();
      if (original == null) return; // Never overwrite another hook's clearing decision.
      if ((access.flags(frame.receiver()) & 0x3f) != 4) return;
      if (original != access.disabledFilter()) return; // Identity, never equals().
      Object replacement = access.normalFilter(frame.receiver());
      frame.replace(replacement);
      log.emit(BoundedLog.Event.HIT);
    } catch (Throwable ignored) {
      log.emit(BoundedLog.Event.ERROR); // Reflection/linkage failure leaves original intact.
    }
  }
}
