// 只拆分两个展示入口，沿用原会话投影、计费口径和 DialogPill 详情交互。
const UsagePill = (0, react.memo)(function UsagePill({ useProjection, usePerformanceUsage, t }) {
  const mode = usePerformanceUsage(value => value);
  const usage = useProjection("tokenUsage");
  if (usage === void 0 || billedInputTokens(usage) === 0 && usage.outputTokens === 0) return null;
  const cacheHit = cacheHitPercent(usage);
  const cacheHitText = cacheHit !== null ? t("stats.cacheHit", { percent: cacheHit }) : null;
  const icon = react.createElement(_deepseek_ai_dsh_client_ui_primitives.IconDatabaseOutlineRegular);
  if (mode === "compact") return cacheHitText === null ? null : react.createElement(PlainPill, { stat: "usage", icon, label: cacheHitText });
  const total = billedInputTokens(usage) + usage.outputTokens;
  const totalText = t("message.turnUsage.count", { count: formatTokens(total, t) });
  const h = react.createElement, pair = (key, label, value) => [h("dt", { key: key + "-label" }, label), h("dd", { key }, value)];
  const title = t("stats.dialog.usageTitle"), cacheTitle = t("message.turnUsage.cacheHit");
  const unavailable = cacheTitle === "缓存命中" ? "未提供" : "Unavailable";
  return h(react.Fragment, null,
    h(DialogPill, { stat: "usage", icon, label: totalText, ariaLabel: title + " · " + totalText, title, titleValue: exactCount(total, t) },
      h("dl", { className: stat_dialog_module_css_default.details, "data-session-stats-usage": true },
        cacheHit !== null ? pair("hit", t("message.turnUsage.cacheHit"), `${cacheHit}%`) : null,
        pair("input", t("message.turnUsage.input"), exactCount(usage.uncachedInputTokens, t)),
        pair("read", t("message.turnUsage.cacheRead"), exactCount(usage.cacheReadTokens, t)),
        usage.cacheWriteTokens !== 0 ? pair("write", t("message.turnUsage.cacheWrite"), exactCount(usage.cacheWriteTokens, t)) : null,
        pair("output", t("message.turnUsage.output"), exactCount(usage.outputTokens, t))
      )
    ),
    h(DialogPill, { stat: "cache", icon: null, label: cacheHitText ?? `${cacheTitle} ${unavailable}`, ariaLabel: cacheHitText ?? `${cacheTitle} ${unavailable}`, title: cacheTitle, titleValue: cacheHit === null ? unavailable : `${cacheHit}%` },
      h("dl", { className: stat_dialog_module_css_default.details, "data-dsha-cache-detail": true },
        pair("read", t("message.turnUsage.cacheRead"), exactCount(usage.cacheReadTokens, t)),
        pair("input", t("message.turnUsage.input"), exactCount(usage.uncachedInputTokens, t)),
        usage.cacheWriteTokens !== 0 ? pair("write", t("message.turnUsage.cacheWrite"), exactCount(usage.cacheWriteTokens, t)) : null
      )
    )
  );
});
