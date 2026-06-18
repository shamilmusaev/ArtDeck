# -*- coding: utf-8 -*-
import unittest

from steam import steamproc
from steam.steamproc import CREATE_NO_WINDOW


class FakeRun:
    def __init__(self, stdout=""):
        self.stdout = stdout
        self.calls = []
        self.kwargs = []

    def __call__(self, args, **kw):
        self.calls.append(args)
        self.kwargs.append(kw)
        return self


class SteamProcTest(unittest.TestCase):
    def test_is_running_true_false(self):
        self.assertTrue(steamproc.is_running(runner=FakeRun("steam.exe  1234 ...")))
        self.assertFalse(steamproc.is_running(runner=FakeRun("INFO: No tasks")))

    def test_is_running_passes_no_window_flag(self):
        fake = FakeRun("steam.exe 1234")
        steamproc.is_running(runner=fake)
        self.assertEqual(fake.kwargs[0].get("creationflags"), CREATE_NO_WINDOW)

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

    def test_shutdown_passes_no_window_flag(self):
        fake = FakeRun()
        steamproc.shutdown(
            "C:\\Steam",
            runner=fake,
            sleep=lambda s: None,
            check=lambda: False,
        )
        self.assertEqual(fake.kwargs[0].get("creationflags"), CREATE_NO_WINDOW)

    def test_launch(self):
        self.assertTrue(steamproc.launch("C:\\Steam", runner=FakeRun()))

    def test_launch_passes_no_window_flag(self):
        fake = FakeRun()
        steamproc.launch("C:\\Steam", runner=fake)
        self.assertEqual(fake.kwargs[0].get("creationflags"), CREATE_NO_WINDOW)
