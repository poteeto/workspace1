package com.deepseekharness.app.util;

import static org.junit.Assert.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.Test;

/** Exercises the same strict adapter invoked by Android's real installer. */
public class LanSettingsCompatibilityTest {
  private static final String HOST =
      "window.__ModuleLoader__.load({id: \"@deepseek-ai/dsh-client-ui-settings\"," +
      "this.ctx.remote.settings.describe(); this.ctx.remote.settings.mutate(" +
      "settings/document-updated; remote.settings});";

  @Test
  public void oldBrowserLoopbackConditionalIsReplacedOnceAndRemainsIdempotent() {
    String src = "before\n" + LanSettingsCompatibility.OLD + "\nafter";
    String patched = LanSettingsCompatibility.adapt(src, "0.2.0-rc.2");
    assertEquals("before\n" + LanSettingsCompatibility.REPLACEMENT + "\nafter", patched);
    assertEquals(patched, LanSettingsCompatibility.adapt(patched, "0.2.0-rc.2"));
  }

  @Test
  public void newHostSettingsProtocolRequiresNoLegacyPatch() {
    assertSame(HOST, LanSettingsCompatibility.adapt(HOST, "0.2.1-rc.2"));
    assertEquals(HOST, LanSettingsCompatibility.adapt(
        LanSettingsCompatibility.adapt(HOST, "0.2.1-rc.2"), "0.2.1-rc.2"));
  }

  @Test
  public void malformedAndUnreviewedChangesFailWithoutEditingFiles() {
    for (String src : new String[] {
        "", LanSettingsCompatibility.OLD, "const persistence = \"memory\";",
        HOST.replace("this.ctx.remote.settings.mutate(", ""),
        HOST.replace("settings/document-updated", ""),
        HOST + LanSettingsCompatibility.OLD }) {
      assertThrows(IllegalArgumentException.class,
          () -> LanSettingsCompatibility.adapt(src, "0.2.1-rc.2"));
    }
    assertThrows(IllegalArgumentException.class,
        () -> LanSettingsCompatibility.adapt(HOST, "0.2.2-rc.1"));
  }

  @Test
  public void realPublishedDshModuleMustSatisfyHostSettingsProtocolWhenAvailable()
      throws Exception {
    String filename = System.getenv("DSHA_REAL_DSH_SETTINGS_MODULE");
    if (filename == null || filename.isEmpty()) return; // Optional for local fixture-only runs.
    String src = Files.readString(Path.of(filename), StandardCharsets.UTF_8);
    assertTrue(src.length() > 1000);
    assertEquals(src, LanSettingsCompatibility.adapt(src, "0.2.1-rc.2"));
  }
}
