# -*- coding: utf-8 -*-
import unittest

from steam import steamproc


class FakeRun:
    def __init__(self, stdout=""):
        self.stdout = stdout
        self.calls = []

    def __call__(self, args, **kw):
        self.calls.append(args)
        return self


class SteamProcTest(unittest.TestCase):
    def test_is_running_true_false(self):
        self.assertTrue(steamproc.is_running(runner=FakeRun("steam.exe  1234 ...")))
        self.assertFalse(steamproc.is_running(runner=FakeRun("INFO: No tasks")))

    def test_shutdown_waits_until_gone(self):
        states = [True, True, False]
        calls = []
        ok = steamproc.shutdown(
            "C:\\Steam",
            runner=FakeRun(),
            sleep=lambda s: calls.append(s),
            check=lambda: states.pop(0) if states else False,
        )
        self.assertTrue(ok)

    def test_launch(self):
        self.assertTrue(steamproc.launch("C:\\Steam", runner=FakeRun()))
