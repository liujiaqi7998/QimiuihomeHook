package com.miui.home.common.utils;

import android.graphics.LightingColorFilter;

public class ProgressIconUtils {
  public static LightingColorFilter filter = new LightingColorFilter(0, 0);

  public static final LightingColorFilter getProgressFilter() {
    return filter;
  }
}
