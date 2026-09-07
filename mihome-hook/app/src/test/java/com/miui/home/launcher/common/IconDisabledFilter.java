package com.miui.home.launcher.common;

import android.graphics.ColorFilter;

public class IconDisabledFilter {
  private static final IconDisabledFilter INSTANCE = new IconDisabledFilter();
  public static ColorFilter filter = new ColorFilter();

  public static IconDisabledFilter getInstance() {
    return INSTANCE;
  }

  public ColorFilter getDisabledColorFilter() {
    return filter;
  }
}
