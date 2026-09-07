package com.miui.home.launcher;

import android.graphics.ColorFilter;

public class ShortcutInfo extends com.miui.home.model.api.ItemInfoWithIconAndMessage {
  public SystemAppStubConfig config;

  public ColorFilter getColorFilter() {
    return null;
  }

  public SystemAppStubConfig getSystemApplicationConfig() {
    return config;
  }
}
