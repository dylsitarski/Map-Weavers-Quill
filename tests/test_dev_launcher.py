"""Regression for repeated termination signals during launcher cleanup."""

import runpy
import signal
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class LauncherTests(unittest.TestCase):
    def test_repeated_signals_do_not_interrupt_child_cleanup(self):
        handlers = {}
        children = [Mock(pid=101), Mock(pid=102)]
        for child in children:
            child.poll.return_value = None

        def terminate(*args):
            handlers[signal.SIGTERM](signal.SIGTERM, None)
            handlers[signal.SIGTERM](signal.SIGTERM, None)

        with (
            patch("signal.signal", side_effect=lambda sig, fn: handlers.update({sig: fn})),
            patch("subprocess.Popen", side_effect=children),
            patch("time.sleep", side_effect=terminate),
            patch("os.killpg", side_effect=terminate) as kill,
        ):
            runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/dev.py"))
        self.assertEqual([call.args[0] for call in kill.call_args_list], [101, 102])
        for child in children:
            child.wait.assert_called_once_with(timeout=5)
