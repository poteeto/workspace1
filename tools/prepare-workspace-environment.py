#!/usr/bin/env python3
"""锁定 rc2 的搜索程序选择和错误原因显示；不重放命令或网络请求。"""
import argparse, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'app/src/main/assets'
CAUSES='''// DSHA_TOOL_FAILURE_CODES_V1：只显示受限错误码，不复制 URL、请求头或环境值。
function dshaFailureCodes(error) {
    const seen=new Set(), codes=new Set();
    function visit(value, depth) {
        if (!value || typeof value!=="object" || seen.has(value) || depth>4 || seen.size>=16) return;
        seen.add(value);
        if (typeof value.code==="string" && /^[A-Z][A-Z0-9_]{1,63}$/.test(value.code)) codes.add(value.code);
        visit(value.cause, depth+1);
        if (Array.isArray(value.errors)) for (const child of value.errors.slice(0,8)) visit(child,depth+1);
    }
    visit(error,0);
    return codes.size ? ` [${[...codes].join(", ")}]` : "";
}
'''

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--modules',type=Path,default=ROOT/'tools/dsh-runtime/node_modules');parser.add_argument('--write',action='store_true');args=parser.parse_args()
    definitions=[('workspace-search-runtime-patch.json','@deepseek-ai/dsh-tool-fs-search/lib/index.js',[
        ('let rgPathPromise;',CAUSES+'let rgPathPromise;'),
        ('\t\tconst executable = parse(process.execPath);','''        // npm 的 ARM64 rg 是静态 ELF，bxroot 的线程限制拒绝静态子进程。
        // Android 固定使用签名 APK 中的 Ubuntu glibc 版本；仍通过原 subprocess 执行。
        if (process.platform === "linux" && process.arch === "arm64" && process.env.DSHA_ANDROID_RUNTIME === "1") {
            const androidRg="/usr/local/bin/rg";
            if (!existsSync(androidRg)) throw Object.assign(new Error("Android glibc ripgrep is missing; runtime preparation is incomplete"), {code:"DSHA_RG_MISSING"});
            return androidRg;
        }
\t\tconst executable = parse(process.execPath);'''),
        ('(ripgrep launch failed)`','(ripgrep launch failed)${dshaFailureCodes(error)}`'),
        ('(ripgrep provider failure)`','(ripgrep provider failure)${dshaFailureCodes(error)}`')
    ]),('workspace-web-errors-patch.json','@deepseek-ai/dsh-web-fetch-http/lib/index.js',[
        ('function translateAbortOrNetwork(error, signal) {',CAUSES+'function translateAbortOrNetwork(error, signal) {'),
        ('`web fetch failed: ${String(error)}`','`web fetch failed: ${String(error)}${dshaFailureCodes(error)}`')
    ])]
    for name,module,pairs in definitions:
        original=(args.modules/module).read_text(encoding='utf-8');current=original
        for before,after in pairs:
            if current.count(before)!=1:raise ValueError('WORKSPACE_ENV_ANCHOR:'+name+':'+before)
            current=current.replace(before,after,1)
        spec={'version':1,'dshVersion':'0.2.1-rc.2','module':module,'sourceSha256':hashlib.sha256(original.encode()).hexdigest(),'patches':[{'before':before,'after':after} for before,after in pairs]}
        contents=json.dumps(spec,ensure_ascii=False,indent=2)+'\n';target=ASSETS/name
        if args.write:target.write_text(contents,encoding='utf-8',newline='\n')
        elif target.read_text(encoding='utf-8')!=contents:raise ValueError('WORKSPACE_ENV_GENERATED_CHANGED:'+name)
    print('PASS workspace search/runtime and network diagnostics recipes')

if __name__=='__main__':main()
