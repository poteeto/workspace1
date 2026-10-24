#!/usr/bin/env python3
"""在原生 ARM64 Linux 中执行同次 APK 的 bxroot/Node/rg；不表示 Android 真机通过。"""
import argparse, os, platform, subprocess, tarfile, tempfile, zipfile
from pathlib import Path, PurePosixPath
ROOT=Path(__file__).resolve().parents[1]

def main(apk):
    if platform.machine() not in ('aarch64','arm64'):raise ValueError('NATIVE_ARM64_REQUIRED')
    with tempfile.TemporaryDirectory(prefix='dsha-workspace-engine-') as scratch:
        work=Path(scratch);rootfs=work/'rootfs';native=work/'native';rootfs.mkdir();native.mkdir()
        with zipfile.ZipFile(apk) as archive:
            for name in ['offline-rootfs.bin','ubuntu-tools.bin','dsh-runtime.bin']:
                payload=work/name;payload.write_bytes(archive.read('assets/'+name))
                with tarfile.open(payload,'r:gz') as tree:
                    for member in tree:
                        rel=PurePosixPath(member.name)
                        if rel.is_absolute() or '..' in rel.parts:raise ValueError('UNSAFE_PINNED_ARCHIVE_PATH')
                    # 已由同次 APK/构建资源摘要核验的 Ubuntu 原始符号链接须保留。
                    tree.extractall(rootfs,filter='fully_trusted')
            for name in ['libbxroot.so','libbxroot-runtime.so','libbxroot-ulx.so']:
                target=native/name;target.write_bytes(archive.read('lib/arm64-v8a/'+name));target.chmod(0o755)
            rg=rootfs/'usr/local/bin/rg';rg.parent.mkdir(parents=True,exist_ok=True);rg.write_bytes(archive.read('assets/ripgrep/rg.bin'));rg.chmod(0o755)
        (rootfs/'tmp').mkdir(exist_ok=True);l2s=rootfs/'.l2s';l2s.mkdir(exist_ok=True)
        env={key:value for key,value in os.environ.items() if not key.startswith(('BXROOT_','PROOT_','PROROOT_','DSH_')) and key not in ('LD_PRELOAD','LD_LIBRARY_PATH')}
        env.update(BXROOT_LIB_PATH=str(native/'libbxroot-runtime.so'),BXROOT_TMP_DIR=str(work),BXROOT_L2S_DIR=str(l2s),BXROOT_REENTRY='0',BXROOT_AUTO_HOST='0',DSHA_BXROOT_STRICT_EXEC='1',DSHA_ANDROID_RUNTIME='1',DSHA_TEST_BXROOT='1',DSHA_TEST_RUNTIME='/usr/local/lib/node_modules/@deepseek-ai/dsh',TMPDIR='/tmp')
        argv=[str(native/'libbxroot.so'),'-r',str(rootfs),'-0','-l','-w','/dsha-testrepo','--kill-on-exit','-b','/proc:/proc','-b','/dev:/dev','-b',str(ROOT)+':/dsha-testrepo','-b',str(l2s)+':'+str(l2s),'/bin/bash','-c','node tools/test-workspace-environment.mjs']
        subprocess.run(argv,env=env,check=True,timeout=180)
    print('PASS same-run APK ARM64 Linux engine search; Android OEM/device acceptance NOT RUN')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('apk',type=Path);args=p.parse_args();main(args.apk)
