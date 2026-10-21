#!/usr/bin/env python3
"""Render legacy Android launcher PNGs from the same official DeepSeek whale
VectorDrawable that API 26+ uses.

Source: https://github.com/deepseek-ai/DeepSeek-LLM/blob/main/images/logo.svg
The original whale path is copied without changing its geometry. The owner's
chosen appearance is black background / white whale (icon option 02).
This is an unofficial DSHA fork; not an official DeepSeek application.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DRAWABLE = ROOT / "app/src/main/res/drawable/dsha_launcher_foreground.xml"
RES = ROOT / "app/src/main/res"

DENSITIES = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
FILES = ("ic_launcher.png", "ic_launcher_v137.png", "ic_launcher_round_v137.png")
ANDROID = "{http://schemas.android.com/apk/res/android}"


def launcher_svg() -> str:
    vector = ET.parse(DRAWABLE).getroot()
    group = vector.find("group")
    if group is None:
        raise ValueError("Missing vector <group>")
    path = group.find("path")
    if path is None:
        raise ValueError("Missing vector <path>")
    d = path.get(ANDROID + "pathData", "")
    if len(d) < 3000 or not d.startswith("M55.6128 "):
        raise ValueError("Unexpected DeepSeek whale vector; refusing to render")
    if path.get(ANDROID + "fillColor") != "#FFFFFFFF":
        raise ValueError("Foreground needs to be pure white")
    sx = group.attrib[ANDROID + "scaleX"]
    sy = group.attrib[ANDROID + "scaleY"]
    tx = group.attrib[ANDROID + "translateX"]
    ty = group.attrib[ANDROID + "translateY"]
    # Rounded square mimics the black-background launcher icon selected by the owner.
    # Transparent corners let legacy launchers preserve the intended silhouette.
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 108 108">'
        '<rect x="0" y="0" width="108" height="108" rx="22" fill="#000"/>'
        f'<g transform="translate({tx} {ty}) scale({sx} {sy})">'
        f'<path fill="#fff" d="{d}"/></g></svg>'
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail when generated PNGs differ")
    args = parser.parse_args()
    try:
        import cairosvg
    except ImportError as exc:
        raise SystemExit("Install CairoSVG first: python -m pip install cairosvg==2.7.1") from exc
    svg = launcher_svg().encode("utf-8")
    wrong = []
    for density, size in DENSITIES.items():
        folder = RES / f"mipmap-{density}"
        image = cairosvg.svg2png(bytestring=svg, output_width=size, output_height=size)
        for name in FILES:
            dest = folder / name
            if args.check:
                if not dest.exists() or dest.read_bytes() != image:
                    wrong.append(str(dest.relative_to(ROOT)))
            else:
                folder.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(image)
                print(f"Created {dest.relative_to(ROOT)} ({size}x{size})")
    if wrong:
        raise SystemExit("Out-of-date launcher PNGs: " + ", ".join(wrong))
    if args.check:
        print("All 15 legacy launcher PNGs match the official whale vector.")


if __name__ == "__main__":
    main()
