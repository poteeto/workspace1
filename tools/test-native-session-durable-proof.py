#!/usr/bin/env python3
"""真实 Linux 内核回归：断开 Java 控制连接也必须保留 native ECHILD 证明。"""
import os
from pathlib import Path
import select
import shutil
import signal
import socket
import subprocess
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]


class DurableProofTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory(prefix='dsha-durable-proof-')
        cls.binary = Path(cls.work.name) / 'session'
        compiler = shutil.which('cc') or shutil.which('gcc')
        subprocess.run([compiler, '-std=c11', '-D_GNU_SOURCE', '-DDSHA_SESSION_TEST', '-O2', '-Wall', '-Wextra', '-Werror',
                        str(ROOT / 'tools/native-session/session-launcher.c'), '-o', str(cls.binary)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def launch(self, script='sleep 30', wrong_birth=False, hide_proc=False):
        temporary = tempfile.TemporaryDirectory(dir=self.work.name)
        self.addCleanup(temporary.cleanup)
        entry = Path(temporary.name) / str(uuid.uuid4())
        entry.mkdir(mode=0o700)
        (entry / 'intent').write_text(entry.name + '\n')
        (entry / 'protocol').write_text('DSHA_OWNED_TREE_V2\n')
        name = 'dsha-proof-' + uuid.uuid4().hex
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(server.close)
        server.bind('\0' + name); server.listen(1); server.settimeout(3)
        child = subprocess.Popen([str(self.binary), '--control=' + name, '--receipt-dir=' + str(entry),
                                  '--', '/bin/sh', '-c', script], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 env={**os.environ, **({'DSHA_SESSION_TEST_HIDE_PROC':'1'} if hide_proc else {})})
        def cleanup():
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=3)
            child.stdout.close(); child.stderr.close()
        self.addCleanup(cleanup)
        self.assertTrue(select.select([child.stdout], [], [], 3)[0])
        stat = child.stdout.readline().decode().removeprefix('DSHA_SESSION_STAT_V1 ')
        birth = stat.rsplit(')', 1)[1].split()[19]
        identity = f'{entry.name}\n{child.pid} {int(birth) + int(wrong_birth)} {child.pid}\n'
        (entry / 'identity').write_text(identity)
        control, _ = server.accept(); control.settimeout(5)
        self.addCleanup(control.close)
        reader = control.makefile('rb'); self.addCleanup(reader.close)
        self.assertEqual(b'READY DSHA_OWNED_TREE_V2\n', reader.readline())
        return child, entry, identity, control, reader

    def test_disconnect_before_exit_preserves_proof_without_java_or_commit(self):
        child, entry, identity, control, reader = self.launch()
        control.sendall(b'START\n')
        self.assertEqual(b'STARTED\n', reader.readline())
        reader.close(); control.close()
        self.assertEqual(143, child.wait(timeout=6))
        self.assertEqual(identity + 'ECHILD 143\n', (entry / 'tree-empty').read_text())
        self.assertFalse((entry / 'tree-empty.native').exists())

    def test_proof_is_durable_before_notification_and_missing_commit_keeps_command_code(self):
        child, entry, identity, control, reader = self.launch('exit 7')
        control.sendall(b'START\n')
        self.assertEqual(b'STARTED\n', reader.readline())
        self.assertEqual(b'COMMAND_EXITED 7\n', reader.readline())
        self.assertEqual(b'OWNED_TREE_EMPTY ECHILD\n', reader.readline())
        self.assertEqual(identity + 'ECHILD 7\n', (entry / 'tree-empty').read_text())
        self.assertIsNone(child.poll(), 'normal connection still waits for COMMIT')
        reader.close(); control.close()
        self.assertEqual(7, child.wait(timeout=3))

    def test_live_detached_descendant_has_no_proof(self):
        child, entry, identity, control, reader = self.launch('setsid sleep 30 & echo $!; exit 0', hide_proc=True)
        control.sendall(b'START\n')
        self.assertEqual(b'STARTED\n', reader.readline())
        descendant = int(child.stdout.readline())
        self.addCleanup(lambda: os.kill(descendant, signal.SIGKILL) if Path(f'/proc/{descendant}').exists() else None)
        self.assertEqual(b'COMMAND_EXITED 0\n', reader.readline())
        self.assertFalse(select.select([control], [], [], .15)[0])
        self.assertFalse((entry / 'tree-empty').exists(), 'leader exit and empty old session cannot prove tree empty')
        self.assertIsNone(child.poll())
        os.kill(descendant, signal.SIGKILL)
        self.assertEqual(b'OWNED_TREE_EMPTY ECHILD\n', reader.readline())
        control.sendall(b'COMMIT\n')
        self.assertEqual(0, child.wait(timeout=3))
        self.assertEqual(identity + 'ECHILD 0\n', (entry / 'tree-empty').read_text())

    def test_reused_or_mismatched_birth_never_launches_guest_or_writes_proof(self):
        child, entry, identity, control, reader = self.launch('echo SHOULD_NOT_RUN', wrong_birth=True)
        control.sendall(b'START\n')
        self.assertEqual(125, child.wait(timeout=3))
        self.assertFalse((entry / 'tree-empty').exists())
        self.assertNotIn(b'SHOULD_NOT_RUN', child.stdout.read())
        self.assertIn(b'DSHA_SESSION_RECEIPT_IDENTITY', child.stderr.read())

    def test_existing_receipt_cannot_be_overwritten(self):
        child, entry, identity, control, reader = self.launch('exit 0')
        (entry / 'tree-empty').write_text(identity + 'ECHILD 99\n')
        control.sendall(b'START\n')
        self.assertEqual(125, child.wait(timeout=3))
        self.assertEqual(identity + 'ECHILD 99\n', (entry / 'tree-empty').read_text())

    def test_symlink_receipt_directory_rejected_before_handshake(self):
        with tempfile.TemporaryDirectory(dir=self.work.name) as temp:
            base = Path(temp); (base / 'real').mkdir(mode=0o700)
            (base / 'link').symlink_to(base / 'real', target_is_directory=True)
            result = subprocess.run([str(self.binary), '--control=unused', '--receipt-dir=' + str(base / 'link'),
                                     '--', '/bin/true'], capture_output=True, timeout=3)
            self.assertEqual(125, result.returncode)
            self.assertIn(b'DSHA_SESSION_RECEIPT_DIRECTORY', result.stderr)


if __name__ == '__main__':
    unittest.main()
