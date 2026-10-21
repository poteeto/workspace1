package com.deepseekharness.app.util;

/**
 * Version-specific compatibility check for DSH client settings storage.
 *
 * 0.2.0 used a browser/loopback conditional and needed a targeted patch to
 * preserve settings across a LAN proxy. 0.2.1 moved all settings mutations to
 * the Host settings RPC service. Applying the 0.2.0 replacement to 0.2.1 can
 * never work and previously aborted the Android runtime installer.
 *
 * Fail closed for unknown revisions or changes to the required Host contract.
 */
public final class LanSettingsCompatibility {
  private LanSettingsCompatibility() {}

  public static final String OLD =
      "const persistence = ctx.remote.$host.isLoopback ? \"host\" : \"memory\";";
  public static final String REPLACEMENT =
      "const persistence = \"host\"; // DSHA patch: LAN 代理场景强制 host 持久化";

  public static String adapt(String source, String dshVersion) {
    if (source == null || dshVersion == null) throw new IllegalArgumentException("LAN_SETTINGS_INPUT");
    switch (dshVersion) {
      case "0.2.0-rc.2":
        return ExactTextPatch.apply(source, OLD, REPLACEMENT);
      case "0.2.1-rc.2":
        // 0.2.1's new settings protocol uses Host-owned snapshot/ordered
        // writes; we must not implant the old browser-local persistence mode.
        if (!source.contains("id: \"@deepseek-ai/dsh-client-ui-settings\"")
            || !source.contains("this.ctx.remote.settings.describe()")
            || !source.contains("this.ctx.remote.settings.mutate(")
            || !source.contains("settings/document-updated")
            || !source.contains("remote.settings")
            || source.contains(OLD)
            || source.contains(REPLACEMENT))
          throw new IllegalArgumentException("LAN_SETTINGS_HOST_RPC_CONTRACT_CHANGED");
        return source;
      default:
        throw new IllegalArgumentException("LAN_SETTINGS_UNREVIEWED_DSH_VERSION");
    }
  }
}
