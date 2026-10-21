#!/usr/bin/env python3
"""Run actual APK-packaged DSH Web *inside the real C session supervisor* on Linux ARM64.

This is a host-kernel/proc simulation of the Android ownership protocol.
The actual APK Android/Bionic, BXROOT, platform permissions and app lifecycle
are NOT exercised here; true device verification is still required.
"""
from __future__ import annotations
import argparse
import html
import http.cookiejar
import os
from pathlib import Path
import re
import select
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time
import threading
import urllib.error
import urllib.request
import urllib.parse
import uuid

def read_stat(pid):
    text=Path(f"/proc/{pid}/stat").read_text()
    left, right=text.rsplit(")",1)
    values=right.strip().split()
    return dict(
        pid=int(left.split(" ",1)[0]),
        state=values[0],
        parent=int(values[1]),
        group=int(values[2]),
        session=int(values[3]),
        started=int(values[19])
    )

def expect_line(fp, deadline, description):
    while time.monotonic()<deadline:
        readable,_,_=select.select([fp],[],[],min(.4,max(0,deadline-time.monotonic())))
        if readable:
            line=fp.readline()
            if not line:raise RuntimeError(f"{description}_EOF")
            return line.decode("utf8","replace").strip()
    raise TimeoutError(description)

def port_free():
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1",0))
        return s.getsockname()[1]

def url_candidates(buffer,port):
    matches=re.findall(r'https?://(?:localhost|127\.0\.0\.1):(\d+)(/[^\s<>"\']*)?',buffer)
    values=[f"http://127.0.0.1:{port}"+path.rstrip(")],.;") for num,path in matches if int(num)==port]
    values.append(f"http://127.0.0.1:{port}/")
    return list(dict.fromkeys(values))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--launcher",type=Path,required=True)
    p.add_argument("--dsh-entry",type=Path,required=True)
    args=p.parse_args()
    assert args.launcher.is_file() and args.dsh_entry.is_file()
    port=port_free()
    name="dsha-kernel-ownership-"+uuid.uuid4().hex
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    root=tempfile.TemporaryDirectory(prefix="dsha-owned-dsh-web-")
    server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    server.bind("\0"+name)
    server.listen(1)
    server.settimeout(6)
    env=os.environ.copy()
    env.update(
        HOME=root.name,
        DSH_HOME=os.path.join(root.name,".dsh"),
        XDG_CONFIG_HOME=os.path.join(root.name,".config"),
        XDG_CACHE_HOME=os.path.join(root.name,".cache"),
        BROWSER="none",
        CI="true",
    )
    for secret in ("DEEPSEEK_API_KEY","OPENAI_API_KEY","ANTHROPIC_API_KEY"):
        env.pop(secret,None)
    child=subprocess.Popen(
        [str(args.launcher),"--birth-handshake",f"--control={name}","--",
         "node",str(args.dsh_entry),"web","--no-open","--port",str(port)],
        stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        env=env,close_fds=True
    )
    connection=None
    started_pid=None
    output=[]
    output_length=[0]
    output_lock=threading.Lock()
    def receive_logs():
        assert child.stdout is not None
        for chunk in iter(child.stdout.readline,b""):
            s=chunk.decode("utf8","replace")
            with output_lock:
                if output_length[0]<64000:
                    output.append(s)
                    output_length[0]+=len(s)
    try:
        assert child.stdout
        deadline=time.monotonic()+7
        birth=expect_line(child.stdout,deadline,"BIRTH_STAT").rstrip("\r\n")
        if not birth.startswith("DSHA_SESSION_STAT_V1 "):
            raise RuntimeError("UNTRUSTED_BIRTH_HANDSHAKE_PREFIX")
        raw=birth[len("DSHA_SESSION_STAT_V1 "):]
        # Signed self-stat is security relevant; require exact process identity.
        observed=read_stat(child.pid)
        claimed=raw.rsplit(")",1)[1].strip().split()
        born_pid=int(raw.split(" ",1)[0])
        started_pid=int(claimed[19])
        assert born_pid==child.pid==observed["pid"]
        assert observed["parent"]==os.getpid()==int(claimed[1])
        assert observed["group"]==observed["session"]==child.pid
        assert observed["group"]==int(claimed[2]) and observed["session"]==int(claimed[3])
        assert observed["started"]==started_pid>0
        assert os.stat(f"/proc/{child.pid}").st_uid==os.getuid()
        connection,_=server.accept()
        ucred=struct.unpack("3i",connection.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
        assert ucred[:2]==(child.pid,os.getuid()),("PEER_MISMATCH",ucred)
        control=connection.makefile("rb",buffering=0)
        assert expect_line(control,time.monotonic()+4,"CONTROL_READY")=="READY DSHA_OWNED_TREE_V2"
        # START is the only authorization to create the actual DSH process.
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
            s.settimeout(.4)
            assert s.connect_ex(("127.0.0.1",port))!=0,"DSH_STARTED_BEFORE_CONTROL_START"
        reader=threading.Thread(target=receive_logs,daemon=True)
        reader.start()
        connection.sendall(b"START\n")
        assert expect_line(control,time.monotonic()+8,"CONTROL_STARTED")=="STARTED"
        started_at=time.monotonic()
        deadline=time.monotonic()+65
        html_page=None
        static_bytes=0
        while time.monotonic()<deadline:
            if child.poll() is not None:raise RuntimeError("C_SUPERVISOR_EXITED_BEFORE_HTTP_READY")
            with output_lock:
                text="".join(output)
            for url in url_candidates(text,port):
                try:
                    with opener.open(url,timeout=2) as result:
                        if result.status!=200:continue
                        body=result.read(256000).decode("utf8","replace")
                        if not ("<!doctype html" in body.lower() and "dsh-client" in body):
                            continue
                        scripts=re.findall(r'<script[^>]+src=["\']([^"\']+)["\']',body,re.I)
                        if not scripts:continue
                        real=html.unescape(scripts[0])
                        target=urllib.parse.urljoin(result.url,real)
                        if urllib.parse.urlsplit(target).hostname not in ("127.0.0.1","localhost"):
                            raise RuntimeError("UNTRUSTED_SCRIPT_URL")
                        with opener.open(target,timeout=5) as asset:
                            if asset.status!=200:continue
                            data=asset.read(200000)
                            if len(data)<64:continue
                            static_bytes=len(data)
                        html_page=body
                        break
                except (urllib.error.URLError,TimeoutError,OSError):
                    continue
            if html_page:break
            time.sleep(.5)
        if not html_page:raise RuntimeError("OWNED_DSH_WEB_NOT_READY")
        assert child.poll() is None
        fresh=read_stat(child.pid)
        assert fresh["started"]==started_pid and fresh["session"]==child.pid
        print("OWNED_KERNEL_BIRTH_RECHECK_PASS pid="+str(child.pid)+" parentVerified=1 sessionVerified=1")
        print("OWNED_CONTROL_START_PASS actualDSHWebProcess=1")
        print("OWNED_DSH_WEB_HTTP_PASS htmlBytes="+str(len(html_page.encode()))+" javascriptBytes="+str(static_bytes)+" elapsed="+f"{time.monotonic()-started_at:.1f}s")
        connection.sendall(b"STOP\n")
        saw_exit=False;saw_empty=False
        deadline=time.monotonic()+18
        while time.monotonic()<deadline and not saw_empty:
            status=expect_line(control,deadline,"CONTROL_CLOSE")
            if status.startswith("COMMAND_EXITED "):
                saw_exit=True
            if status=="OWNED_TREE_EMPTY ECHILD":
                saw_empty=True
        assert saw_exit and saw_empty,("MISSING_REAL_CHILD_EXIT_PROOF",saw_exit,saw_empty)
        connection.sendall(b"COMMIT\n")
        child.wait(timeout=5)
        assert child.returncode is not None
        print("OWNED_DSH_SESSION_CLEAN_EXIT_PASS commandExit=1 kernelECHILD=1")
        print("OWNED_DSH_END_TO_END_PASS platform=linux-arm64 dshVersion=0.2.1-rc.2")
    finally:
        if child.poll() is None:
            try:
                now=read_stat(child.pid)
                if started_pid is not None and now["started"]==started_pid and now["session"]==child.pid:
                    os.killpg(child.pid,signal.SIGKILL)
                else:
                    child.terminate()
            except (ProcessLookupError,FileNotFoundError):
                pass
        try:child.wait(timeout=3)
        except subprocess.TimeoutExpired:pass
        if connection:connection.close()
        server.close()
        root.cleanup()

if __name__=="__main__":
    main()
