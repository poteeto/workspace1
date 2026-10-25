// DSHA 工作区展示组件；模型目录、保存、错误及会话写锁仍由原 ModelSelect 负责。
function dshaWorkspaceMobileSnapshot() { return window.matchMedia("(max-width: 767px)").matches; }
function dshaWorkspaceMobileSubscribe(listener) {
  const media = window.matchMedia("(max-width: 767px)");
  media.addEventListener("change", listener);
  return () => media.removeEventListener("change", listener);
}
function DshaWorkspaceModelRoot({ modelLabel, providerLabel, modelNames, effortChoices, effectiveEffort, busy, error, retry, onModels, onClose, onEffort, t }) {
  const h = react.createElement;
  const zh = t("menu.model") === "模型";
  const copy = zh ? {
    title: "模型与推理强度", effort: "推理强度", faster: "更快", smarter: "更深入", done: "完成", close: "关闭", defaults: "使用模型默认", selected: "已自选档位", defaultSelected: "模型默认", next: "后续请求使用此设置。", unsupported: "此模型未提供可调节的思考强度。"
  } : {
    title: "Model and reasoning", effort: "Reasoning effort", faster: "Faster", smarter: "Smarter", done: "Done", close: "Close", defaults: "Use model default", selected: "Custom effort", defaultSelected: "Model default", next: "Used for subsequent requests.", unsupported: "This model does not advertise adjustable reasoning effort."
  };
  const selected = Math.max(0, effortChoices.findIndex(level => level.effort === effectiveEffort));
  const [draft, setDraft] = react.useState(selected);
  const [dragging, setDragging] = react.useState(false);
  const [lean, setLean] = react.useState(0);
  const track = react.useRef(null), capture = react.useRef(null), valueRef = react.useRef(null);
  const count = effortChoices.length;
  const index = Math.min(draft, Math.max(0, count - 1));
  const level = effortChoices[index];
  const ratio = count > 1 ? index / (count - 1) : 0;
  const max = level?.effort === "max";
  const descriptions = zh ? {
    off: "关闭额外思考，直接处理请求。", minimal: "进行简短思考，优先响应速度。", low: "更快给出结果，适合简短问题。", medium: "兼顾响应速度与思考深度。", high: "更充分地思考，适合分析和排查问题。", xhigh: "投入更多思考，适合复杂任务。", max: "使用最高思考强度，通常需要更长时间。", default: "跟随提供方或模型的默认设置。"
  } : {
    off: "Respond without additional reasoning.", minimal: "Brief reasoning with faster responses.", low: "Faster responses for straightforward questions.", medium: "Balance response speed and reasoning depth.", high: "More reasoning for analysis and troubleshooting.", xhigh: "Additional reasoning for complex tasks.", max: "Maximum reasoning, which may take longer.", default: "Follow the provider or model default."
  };
  const description = item => descriptions[item?.effort] ?? descriptions.default;
  const previous = react.useRef(index);
  react.useEffect(() => setDraft(selected), [selected]);
  react.useEffect(() => {
    const direction = index >= previous.current ? 1 : -1;
    previous.current = index;
    if (!valueRef.current?.animate || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const animation = valueRef.current.animate([
      { transform: `translateY(${direction * .55}em)`, filter: "blur(2px)", opacity: 0 },
      { transform: "translateY(0)", filter: "blur(0)", opacity: 1 }
    ], { duration: 200, easing: "ease-out" });
    return () => animation.cancel();
  }, [index]);
  const slot = (active, values, className) => h("span", { className: "dsha-ws-slot " + (className || "") },
    h("span", null, active), values.map((text, i) => h("span", { key: i, className: "dsha-ws-reserve", "aria-hidden": true }, text)));
  const follow = event => {
    if (!capture.current || !track.current || busy || count < 2) return;
    const box = track.current.getBoundingClientRect(), span = box.width - 24;
    const progress = Math.max(0, Math.min(1, (event.clientX - capture.current.offset - box.left - 12) / span));
    const next = Math.round(progress * (count - 1));
    setDraft(next);
    const delta = (progress - next / (count - 1)) * (count - 1);
    setLean(event.pointerType === "touch" ? 0 : Math.round(Math.sign(delta) * .12 * (1 - Math.exp(-Math.abs(delta) / .12)) * span / (count - 1) * 2) / 2);
  };
  const release = () => { capture.current = null; setDragging(false); setLean(0); };
  return h("div", { className: "dsha-ws-model-root", "data-dsha-workspace-controls": true },
    h("div", { className: "dsha-ws-heading" }, h("strong", null, copy.title), h("button", { type: "button", onClick: onClose, "aria-label": copy.close }, h(_deepseek_ai_dsh_client_ui_primitives.IconCloseOutlineRegular, { size: 18 }))),
    h("div", { className: "dsha-ws-model-body" },
      error ? h("div", { className: "dsha-ws-error", role: "alert" }, h("span", null, t("error.action", { message: error })), h("button", { type: "button", onClick: retry }, t("retry"))) : null,
      h("span", { className: "dsha-ws-provider" }, t("menu.model") + " · " + providerLabel),
      h("button", { type: "button", className: "dsha-ws-model-choice", disabled: busy, onClick: onModels }, slot(modelLabel, modelNames), h(_deepseek_ai_dsh_client_ui_primitives.IconChevronRightOutlineRegular, { size: 16 })),
      count ? h("div", { className: "dsha-ws-effort", "data-max": max },
        h("div", { className: "dsha-ws-effort-heading" }, h("span", null, copy.effort), h("span", { ref: valueRef, className: "dsha-ws-effort-value", "aria-live": "polite" }, level?.label)),
        h("div", { className: "dsha-ws-axis" }, h("span", null, copy.faster), h("span", null, copy.smarter)),
        h("div", { className: "dsha-ws-range", ref: track, "data-dragging": dragging, style: { "--dsha-effort-pos": ratio, "--dsha-effort-lean": `${lean}px` } },
          h("div", { className: "dsha-ws-track", "aria-hidden": true }, h("div", { className: "dsha-ws-fill" }), h(DshaEffortPixels, { active: max })),
          effortChoices.map((item, i) => h("span", { key: item.key, className: "dsha-ws-stop", "aria-hidden": true, "data-selected": index === i, style: { left: `calc(15.5px + (100% - 31px) * ${count > 1 ? i / (count - 1) : 0})` } })),
          h("span", { className: "dsha-ws-thumb", "aria-hidden": true }),
          h("input", {
            type: "range", min: 0, max: Math.max(0, count - 1), step: 1, value: index, disabled: busy || count < 2,
            "aria-label": copy.effort, "aria-valuetext": level?.label,
            onChange: event => setDraft(Number(event.target.value)),
            onPointerDown: event => {
              if (busy || count < 2) return;
              event.preventDefault(); event.currentTarget.focus();
              const box = track.current.getBoundingClientRect();
              const offset = event.clientX - (box.left + 12 + ratio * (box.width - 24));
              capture.current = { id: event.pointerId, offset: Math.abs(offset) <= 8.4 ? offset : 0 };
              event.currentTarget.setPointerCapture(event.pointerId); setDragging(true); follow(event);
            },
            onPointerMove: follow, onPointerUp: release, onPointerCancel: release, onLostPointerCapture: release
          })
        ),
        slot(description(level), Object.values(descriptions), "dsha-ws-description"),
        h("div", { className: "dsha-ws-default-row" }, h("span", null, level?.effort === void 0 ? copy.defaultSelected : copy.selected),
          effortChoices.some(item => item.effort === void 0) ? h("button", { type: "button", className: "dsha-ws-default", disabled: busy, onClick: () => setDraft(effortChoices.findIndex(item => item.effort === void 0)) }, copy.defaults) : null)
      ) : h("p", { className: "dsha-ws-description" }, copy.unsupported),
      h("p", { className: "dsha-ws-note" }, copy.next)
    ),
    h("div", { className: "dsha-ws-model-footer" }, h("button", { type: "button", className: "dsha-ws-done", disabled: busy, onClick: () => level ? onEffort(level.effort) : onClose() }, busy ? h(_deepseek_ai_dsh_client_ui_primitives.StateDot, { state: "ongoing" }) : copy.done))
  );
}

// 本地绘制的像素场，不引入第三方程序包或网络资源；退出菜单时释放全部监听及动画。
function DshaEffortPixels({ active }) {
  const canvasRef = react.useRef(null);
  react.useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d");
    if (!context) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    let frame = 0, start = performance.now(), visible = true;
    const paint = now => {
      const box = canvas.getBoundingClientRect(), dpr = Math.min(window.devicePixelRatio || 1, 2);
      if (!box.width || !box.height) return;
      const w = Math.round(box.width * dpr), ht = Math.round(box.height * dpr);
      if (canvas.width !== w || canvas.height !== ht) { canvas.width = w; canvas.height = ht; }
      context.setTransform(dpr, 0, 0, dpr, 0, 0); context.clearRect(0, 0, box.width, box.height);
      if (!active) return;
      const time = reduced.matches ? 3 : Math.max(0, now - start) / 1000;
      const ink = getComputedStyle(canvas), base = ink.color, bright = ink.outlineColor;
      const pitch = box.height / Math.max(1, Math.round(box.height / 4));
      for (let row = 0; row < box.height / pitch; row++) for (let col = 0; col < box.width / pitch; col++) {
        const x = (col + .5) * pitch, y = (row + .5) * pitch, random = (Math.sin(col * 127.1 + row * 311.7) * 43758.5453 + 43758.5453) % 1;
        const arrival = (box.width - x) / 140 + random * .12;
        if (time < arrival) continue;
        context.globalAlpha = Math.min(1, (time - arrival) * 4) * (.3 + .7 * x / box.width);
        context.fillStyle = base; context.fillRect(x - pitch / 2, y - pitch / 2, pitch, pitch);
        const energy = (.5 + .5 * Math.sin(time * (2 + random) - col * .21 + row * .8)) ** 3;
        if (random > .85) continue;
        context.globalAlpha *= .25 + energy * .7; context.fillStyle = bright;
        if (context.roundRect) { context.beginPath(); context.roundRect(x - 1.5, y - 1.5, 3, 3, .9); context.fill(); }
        else context.fillRect(x - 1.5, y - 1.5, 3, 3);
      }
      context.globalAlpha = 1;
    };
    const loop = now => { paint(now); if (active && visible && !document.hidden && !reduced.matches) frame = requestAnimationFrame(loop); };
    const restart = () => { cancelAnimationFrame(frame); frame = 0; if (!visible || document.hidden) return; paint(performance.now()); if (active && !reduced.matches) frame = requestAnimationFrame(loop); };
    const resize = new ResizeObserver(restart); resize.observe(canvas);
    const observer = typeof IntersectionObserver === "undefined" ? null : new IntersectionObserver(entries => { visible = entries[0].isIntersecting; restart(); }); observer?.observe(canvas);
    document.addEventListener("visibilitychange", restart); reduced.addEventListener("change", restart); restart();
    return () => { cancelAnimationFrame(frame); resize.disconnect(); observer?.disconnect(); document.removeEventListener("visibilitychange", restart); reduced.removeEventListener("change", restart); };
  }, [active]);
  return react.createElement("canvas", { ref: canvasRef, className: "dsha-ws-pixels", "aria-hidden": true });
}
