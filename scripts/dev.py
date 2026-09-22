"""Start both loopback services; stop the other if either exits."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
env = dict(os.environ, PYTHONPATH=str(root / "apps/server"))
processes: list[subprocess.Popen[bytes]] = []
stopping = False


def stop(signum, frame):
    global stopping
    stopping = True


signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
try:
    processes.append(
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "quill.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            cwd=root,
            env=env,
            start_new_session=True,
        )
    )
    processes.append(subprocess.Popen(["npm", "run", "dev"], cwd=root, start_new_session=True))
    while not stopping and all(p.poll() is None for p in processes):
        time.sleep(0.2)
    if not stopping:
        raise SystemExit(next(p.returncode for p in processes if p.returncode is not None))
finally:
    # A signal may arrive both directly and forwarded by make. Handlers only set
    # the flag, so repeated signals cannot interrupt this bounded cleanup.
    for process in processes:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    for process in processes:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
