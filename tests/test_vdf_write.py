# -*- coding: utf-8 -*-
"""Round-trip and backup tests for the binary shortcuts.vdf writer."""
import os
import tempfile
import unittest

from steam.vdf import parse_binary_vdf
from steam.vdf_write import dump_binary_vdf, write_shortcuts, read_shortcuts_map


SAMPLE = {
    "0": {"appid": -2147483648, "AppName": "Game One", "Exe": "\"C:\\g\\one.exe\"",
          "StartDir": "\"C:\\g\"", "icon": "", "IsHidden": 0, "AllowOverlay": 1,
          "tags": {"0": "ArtDeck"}},
    "1": {"appid": -5, "AppName": "Two", "Exe": "\"C:\\g\\two.exe\"",
          "StartDir": "\"C:\\g\"", "icon": "", "tags": {}},
}


class VdfWriteTest(unittest.TestCase):
    def test_round_trip(self):
        self.assertEqual(parse_binary_vdf(dump_binary_vdf(SAMPLE)), SAMPLE)

    def test_write_creates_backup_and_reads_back(self):
        with tempfile.TemporaryDirectory() as d:
            vdf = os.path.join(d, "shortcuts.vdf")
            # first write: no prior file -> no backup
            self.assertIsNone(write_shortcuts(vdf, SAMPLE))
            self.assertEqual(read_shortcuts_map(vdf), SAMPLE)
            # second write: backs up the old file
            bak = write_shortcuts(vdf, {"0": SAMPLE["0"]})
            self.assertEqual(bak, vdf + ".bak")
            self.assertTrue(os.path.isfile(bak))
            self.assertEqual(read_shortcuts_map(vdf), {"0": SAMPLE["0"]})

    def test_missing_file_reads_empty(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(read_shortcuts_map(os.path.join(d, "nope.vdf")), {})
