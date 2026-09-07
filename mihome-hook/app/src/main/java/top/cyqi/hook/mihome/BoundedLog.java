package top.cyqi.hook.mihome;

import java.util.function.Consumer;

/** Fixed strings only, no package lists/user data/stacktrace spam. Per-process budget <= 7. */
final class BoundedLog {
  enum Event {
    WAITING,
    INSTALLED,
    SKIPPED,
    HIT,
    ERROR
  }

  private final Consumer<String> sink;
  private final int[] counts = new int[Event.values().length];

  BoundedLog(Consumer<String> sink) {
    this.sink = sink;
  }

  synchronized void emit(Event event) {
    int index = event.ordinal();
    if (counts[index] >= (event == Event.ERROR ? 3 : 1)) return;
    counts[index]++;
    try {
      sink.accept("[MiHomeColor] " + event.name());
    } catch (Throwable ignored) {
      /* Diagnostics must never break the launcher. */
    }
  }
}
