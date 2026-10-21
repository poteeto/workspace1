#!/usr/bin/env python3
"""Fail closed when a DSHA patch no longer matches its published DSH module."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
assets = root / "app/src/main/assets"
packages = root / "tools/dsh-runtime/node_modules"
registry = json.loads((assets / "runtime-patches.json").read_text())
version = json.loads((root / "tools/dsh-runtime/package.json").read_text())["dependencies"]["@deepseek-ai/dsh"]
report = []
for row in registry["active"]:
    name = row["asset"]
    recipe_path = assets / name
    recipe = json.loads(recipe_path.read_text())
    module = row.get("module") or recipe.get("module")
    if not isinstance(module, str):
        report.append((name, "NO_MODULE", 0, ""))
        continue
    target = packages / module
    if not target.is_file():
        report.append((name, "NO_FILE", 0, module))
        continue
    source = target.read_text(encoding="utf8")
    failures = []
    for index, patch in enumerate(recipe.get("patches", [])):
        before = patch.get("before", "")
        count = source.count(before) if before else 0
        if count != 1:
            failures.append(str(index) + ":" + str(count))
        else:
            source = source.replace(before, patch.get("after", ""))
    status = "READY" if not failures else "CHANGED"
    report.append((name, status, len(recipe.get("patches", [])), ",".join(failures)))
for name, status, count, info in report:
    print(f"{status:9} {name:48} patches={count:<3} {info}")
print(f"Checked {len(report)} regular patch recipes for DSH {version}")
if any(x[1] != "READY" for x in report):
    raise SystemExit("PATCH_ANCHORS_CHANGED")
