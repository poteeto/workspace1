#!/usr/bin/env python3
"""Summarize actual zipped bytes in a DSHA APK (read-only).

This report distinguishes download bytes from uncompressed payload size.
Never deletes, replaces, or weakens a checked-in runtime, policy, or recovery asset.
"""
from __future__ import annotations
import argparse
import collections
import json
from pathlib import Path
import zipfile

def bucket(path: str) -> str:
    if path.startswith("assets/offline-rootfs.bin"): return "Ubuntu base rootfs"
    if path.startswith("assets/dsh-runtime.bin"): return "Current DSH runtime"
    if path.startswith("assets/recovery-rootfs.bin"): return "Recovery base rootfs"
    if path.startswith("assets/recovery-dsh-runtime.bin"): return "Recovery DSH runtime"
    if path.startswith("assets/ubuntu-tools.bin"): return "Ubuntu package tools"
    if path.startswith("assets/pnpm-runtime.bin"): return "pnpm runtime"
    if path.startswith("assets/python-support.bin") or "python" in path and path.startswith("assets/"): return "Python support"
    if path.startswith("assets/"): return "Other APK assets"
    if path.startswith("lib/"): return "Android native libraries"
    if path.startswith("res/") or path.startswith("resources.arsc"): return "Android UI resources"
    if path.startswith("classes") and path.endswith(".dex"): return "Android DEX"
    if path.startswith("META-INF/"): return "Metadata"
    return "Other APK entries"

def analyze(filename: str) -> dict:
    file=Path(filename)
    groups=collections.defaultdict(lambda: [0,0,0])
    with zipfile.ZipFile(file) as apk:
        members=[e for e in apk.infolist() if not e.is_dir()]
        for e in members:
            group=groups[bucket(e.filename)]
            group[0]+=e.compress_size
            group[1]+=e.file_size
            group[2]+=1
        largest=sorted(members,key=lambda z:z.compress_size,reverse=True)[:35]
        rows=[dict(name=e.filename,compressed=e.compress_size,uncompressed=e.file_size,method="STORED" if e.compress_type==0 else "DEFLATE") for e in largest]
    return dict(file=file.name,bytes=file.stat().st_size,entries=len(members),groups=[dict(name=n,compressed=p[0],uncompressed=p[1],files=p[2]) for n,p in sorted(groups.items(),key=lambda x:x[1][0],reverse=True)],largest=rows)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("apk",nargs="+")
    parser.add_argument("--json",default="")
    args=parser.parse_args()
    results=[analyze(p) for p in args.apk]
    for result in results:
        print("\nAPK SIZE BREAKDOWN",result["file"],"total",result["bytes"],"bytes")
        print("GROUPS (compressed; uncompressed; count)")
        for p in result["groups"]:
            print(f'  {p["compressed"]/1048576:8.2f} MiB | {p["uncompressed"]/1048576:8.2f} MiB | {p["files"]:5} | {p["name"]}')
        print("LARGEST ENTRIES (download contribution)")
        for p in result["largest"][:23]:
            print(f'  {p["compressed"]/1048576:8.2f} MiB | {p["method"]:7} | {p["name"]}')
    if args.json:
        Path(args.json).write_text(json.dumps(results,indent=2)+"\n",encoding="utf-8")
