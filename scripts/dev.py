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


def stop(signum, frame):
    raise KeyboardInterrupt


signal.signal(signal.SIGTERM, stop)
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
        )
    )
    processes.append(subprocess.Popen(["npm", "run", "dev"], cwd=root, start_new_session=True))
    while all(p.poll() is None for p in processes):
        time.sleep(0.2)
    raise SystemExit(next(p.returncode for p in processes if p.returncode is not None))
except KeyboardInterrupt:
    pass
finally:
    for index, process in enumerate(processes):
        if process.poll() is None:
            if index == 1:
                os.killpg(process.pid, signal.SIGTERM)
            else:
                process.terminate()
    for process in processes:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
