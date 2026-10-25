#!/usr/bin/env python3
"""从固定 rc2 客户端的精确锚点生成展示补丁；不修改上游数据/保存协议。"""
from pathlib import Path
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'app/src/main/assets'
SOURCE = ROOT / 'tools/workspace-ui'


def recipe(name, module, original, pairs, write):
    current = original
    for before, after in pairs:
        if current.count(before) != 1:
            raise ValueError('WORKSPACE_UI_ANCHOR:' + name + ':' + before[:100])
        current = current.replace(before, after, 1)
    result = {'version': 1, 'dshVersion': '0.2.1-rc.2', 'module': module,
              'sourceSha256': hashlib.sha256(original.encode()).hexdigest(),
              'patches': [{'before': before, 'after': after} for before, after in pairs]}
    contents = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    target = ASSETS / name
    if write:
        target.write_text(contents, encoding='utf-8', newline='\n')
    elif target.read_text(encoding='utf-8') != contents:
        raise ValueError('WORKSPACE_UI_GENERATED_CHANGED:' + name)
    return current


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--modules', type=Path, default=ROOT / 'tools/dsh-runtime/node_modules')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    model_module = '@deepseek-ai/dsh-client-ui-model-selection/lib/client.js'
    original = (args.modules / model_module).read_text(encoding='utf-8')
    helper = (SOURCE / 'model-controls.js').read_text(encoding='utf-8')
    css = (SOURCE / 'workspace.css').read_text(encoding='utf-8')
    signature = '\t\tfunction ModelSelect({ locked, available, directory, load, select, t, renderSlot }) {'
    helpers = '\n'.join('\t\t' + line if line else '' for line in helper.splitlines()) + '\n'
    root = '''dshaUi && pane !== "model" && (0, react_jsx_runtime.jsx)(DshaWorkspaceModelRoot, {
                                key: JSON.stringify([state.current?.provider, state.current?.model]),
                                modelLabel: currentChoice === void 0 ? modelLabel : renderModelLabel(currentChoice.group.provider, currentChoice.model, "menu", true),
                                providerLabel: currentChoice?.group.provider.name ?? t("menu.model"),
                                modelNames: choices.map(choice => choice.model.name),
                                effortChoices, effectiveEffort, busy,
                                error: state.error !== null && lastActionRef.current === "load" ? state.error : null,
                                retry: reload, onModels: () => drill("model"), onClose: () => close(true), onEffort: chooseEffort, t
                            }),
                            !dshaUi && pane === "root" &&'''
    pairs = [
        ('tag.textContent = css;', 'tag.textContent = css + ' + json.dumps('\n' + css, ensure_ascii=False) + ';'),
        (signature, helpers + signature + '\n\t\t\tconst dshaUi = (0, react.useSyncExternalStore)(dshaWorkspaceMobileSubscribe, dshaWorkspaceMobileSnapshot);'),
        ('\t\t\t\tif (!open) return;\n\t\t\t\tif (pane === "model" && showSearch &&', '\t\t\t\tif (!open) return;\n\t\t\t\t// DSHA_WORKSPACE_UI_V1：滑条保留原生键盘和 Tab，目录继续原来的搜索导航。\n\t\t\t\tif (dshaUi && pane !== "model") return;\n\t\t\t\tif (pane === "model" && showSearch &&'),
        ('if (rootRef.current !== null) closeAfterSelection();', 'if (rootRef.current !== null) { if (dshaUi && pane === "model") { setPane("root"); setSelectionFocus(false); } else closeAfterSelection(); }'),
        ('\t\t\t\t\tcloseAfterSelection();\n\t\t\t\t\treturn;\n\t\t\t\t}\n\t\t\t\tsubmit(selection);', '\t\t\t\t\tif (dshaUi) setPane("root"); else closeAfterSelection();\n\t\t\t\t\treturn;\n\t\t\t\t}\n\t\t\t\tsubmit(selection);'),
        ('"aria-label": triggerAria,', '"aria-label": triggerAria,\n\t\t\t\t\t\t"data-dsha-model-trigger": dshaUi ? true : void 0,'),
        ('role: pane === "model" ? "group" : "menu",', 'role: pane === "model" ? "group" : dshaUi ? "dialog" : "menu",\n\t\t\t\t\t\t"data-dsha-model-menu": dshaUi ? true : void 0,\n\t\t\t\t\t\t"data-dsha-pane": dshaUi ? pane : void 0,'),
        ('"aria-haspopup": "menu",', '"aria-haspopup": dshaUi ? "dialog" : "menu",'),
        ('\t\t\t\t\t\t\t\tshowSearch &&', '''                                dshaUi && (0, react_jsx_runtime.jsxs)("div", { className: "dsha-ws-heading", children: [
                                    (0, react_jsx_runtime.jsx)("button", { type: "button", "aria-label": t("menu.model") === "模型" ? "返回" : "Back", onClick: () => setPane("root"), children: "‹" }),
                                    (0, react_jsx_runtime.jsx)("strong", { children: t("menu.model") }),
                                    (0, react_jsx_runtime.jsx)("button", { type: "button", "aria-label": t("menu.model") === "模型" ? "关闭" : "Close", onClick: () => close(true), children: (0, react_jsx_runtime.jsx)(_deepseek_ai_dsh_client_ui_primitives.IconCloseOutlineRegular, { size: 18 }) })
                                ] }),
                                showSearch &&'''),
        ('\t\t\t\t\t\t\tpane === "root" &&', '\t\t\t\t\t\t\t' + root),
        ('\t\t\t\t\t\t\tpane === "effort" &&', '\t\t\t\t\t\t\t!dshaUi && pane === "effort" &&'),
    ]
    recipe('workspace-model-ui-patch.json', model_module, original, pairs, args.write)
    permission_module = '@deepseek-ai/dsh-client-ui-permission-presets/lib/client.js'
    original = (args.modules / permission_module).read_text(encoding='utf-8')
    # The catalog still owns values, selection and risk confirmation. Only the shipped
    # guarded preset's conventional name is localized, on both current/default pickers.
    pairs = [
        ('function displayPermissionPreset(value, name, t) {', '''function displayPermissionPreset(value, name, t) {
            // DSHA_WORKSPACE_PERMISSION_LABEL_V1
            if (value === "custom" && (name === value || name === "Custom"))
                return t?.("preset.workspaceWrite") === "工作区内修改" ? "自定义" : "Custom";
            if (value === "guarded-full-access" && (name === value || name === "Guarded Full Access"))
                return t?.("preset.workspaceWrite") === "工作区内修改" ? "保护式完全权限" : "Guarded Full Access";'''),
        ('className: PermissionSelect_module_css_default.trigger,', 'className: PermissionSelect_module_css_default.trigger,\n                        "data-dsha-permission-trigger": true,'),
        ('function optionDescription(option, t) {', '''function optionDescription(option, t) {
            if (option.value === "guarded-full-access" && t("preset.workspaceWrite") === "工作区内修改"
                && option.description === "Full file access; destructive or opaque agent commands and existing-file overwrites ask once.")
                return "允许访问全部文件；涉及破坏性命令、不透明命令或覆盖已有文件时，会请求一次确认。";'''),
    ]
    recipe('workspace-permission-ui-patch.json', permission_module, original, pairs, args.write)
    composer_module = '@deepseek-ai/dsh-client-ui-conversation/lib/client.js'
    original = (args.modules / composer_module).read_text(encoding='utf-8')
    recipe('workspace-composer-ui-patch.json', composer_module, original, [
        ('className: ContextMeter_module_css_default.root,', 'className: ContextMeter_module_css_default.root,\n                "data-dsha-context-stat": true,'),
        ('className: InputBar_module_css_default.row,', 'className: InputBar_module_css_default.row,\n                                "data-dsha-composer-toolbar": true,'),
        ('className: clsx(ConversationRoot_module_css_default.header, blank && ConversationRoot_module_css_default.headerBlank, sessionId === void 0 && ConversationRoot_module_css_default.headerSessionless),', 'className: clsx(ConversationRoot_module_css_default.header, blank && ConversationRoot_module_css_default.headerBlank, sessionId === void 0 && ConversationRoot_module_css_default.headerSessionless),\n                "data-dsha-workspace-header": blank ? void 0 : true,'),
        ('className: ConversationRoot_module_css_default.titleRow,', 'className: ConversationRoot_module_css_default.titleRow,\n                "data-dsha-workspace-title": true,'),
        ('className: ConversationRoot_module_css_default.tabs,', 'className: ConversationRoot_module_css_default.tabs,\n                "data-dsha-workspace-tabs": true,'),
    ], args.write)
    chat_module = '@deepseek-ai/dsh-client-ui-chat/lib/client.js'
    original = (args.modules / chat_module).read_text(encoding='utf-8')
    start = original.index('\t\tconst UsagePill = (0, react.memo)(function UsagePill(')
    end = original.index('\n\t\t//#endregion', start)
    usage = '\n'.join('\t\t' + line if line else '' for line in (SOURCE / 'usage-pills.js').read_text(encoding='utf-8').splitlines())
    desktop = original[start:end].replace('const UsagePill =', 'const DefaultUsagePill =', 1)
    mobile = usage.replace('const UsagePill =', 'const MobileUsagePill =', 1)
    wrapper = helpers[:helpers.index('\t\tfunction DshaWorkspaceModelRoot')]
    wrapper += '''\n        const UsagePill = (0, react.memo)(function UsagePill(props) {
            const mobile = (0, react.useSyncExternalStore)(dshaWorkspaceMobileSubscribe, dshaWorkspaceMobileSnapshot);
            return (0, react_jsx_runtime.jsx)(mobile ? MobileUsagePill : DefaultUsagePill, props);
        });
        function DshaWorkspaceActivityLabel({counts, speed}) {
            const mobile = (0, react.useSyncExternalStore)(dshaWorkspaceMobileSubscribe, dshaWorkspaceMobileSnapshot);
            if (!mobile) return joined$1(counts, speed);
            return (0, react_jsx_runtime.jsxs)("span", { "data-dsha-activity-label": true, children: [(0, react_jsx_runtime.jsx)("span", { children: counts }), speed === null ? null : (0, react_jsx_runtime.jsx)("span", { children: speed })] });
        }'''
    pairs = [(original[start:end], desktop + '\n' + mobile + '\n' + wrapper), ('label: joined$1(counts, speed)', 'label: (0, react_jsx_runtime.jsx)(DshaWorkspaceActivityLabel, {counts, speed})')]
    recipe('workspace-stats-ui-patch.json', chat_module, original, pairs, args.write)
    print('PASS workspace UI generated recipes and exact rc2 anchors')


if __name__ == '__main__':
    main()
