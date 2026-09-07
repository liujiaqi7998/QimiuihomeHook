package top.cyqi.hook.mihome;

import static org.junit.Assert.*;

import java.util.*;
import org.junit.Test;

public class BoundedLogTest {
  @Test
  public void eachLifecycleAndHitOnceErrorsAtMostThree() {
    List<String> entries = new ArrayList<>();
    BoundedLog log = new BoundedLog(entries::add);
    for (int n = 0; n < 100; n++) for (BoundedLog.Event e : BoundedLog.Event.values()) log.emit(e);
    assertEquals(7, entries.size());
    assertEquals(3, entries.stream().filter(s -> s.contains("ERROR")).count());
  }

  @Test
  public void brokenLogSinkCannotEscape() {
    new BoundedLog(
            s -> {
              throw new LinkageError();
            })
        .emit(BoundedLog.Event.HIT);
  }
}
