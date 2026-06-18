# -*- coding: utf-8 -*-
import os
import struct
import tempfile
import unittest

from steam import exeicon
from steam.icons import _exe_target


class ExeTargetTest(unittest.TestCase):
    def test_quoted(self):
        self.assertEqual(_exe_target('"C:\\g\\game.exe"'), "C:\\g\\game.exe")

    def test_quoted_with_args(self):
        self.assertEqual(_exe_target('"C:\\g\\game.exe" -windowed'), "C:\\g\\game.exe")

    def test_unquoted(self):
        self.assertEqual(_exe_target("C:\\g\\game.exe"), "C:\\g\\game.exe")

    def test_empty(self):
        self.assertEqual(_exe_target(""), "")
        self.assertEqual(_exe_target(None), "")


class IcoBuildTest(unittest.TestCase):
    def test_group_icon_to_ico(self):
        img = b"\x89PNG fake icon bytes"
        # one GRPICONDIRENTRY: 16x16, 32bpp, referencing RT_ICON id 1
        group = struct.pack("<HHH", 0, 1, 1) + struct.pack(
            "<BBBBHHIH", 16, 16, 0, 0, 1, 32, len(img), 1)
        ico = exeicon._group_icon_to_ico(group, {1: img})
        self.assertEqual(ico[:6], struct.pack("<HHH", 0, 1, 1))  # .ico header
        # entry's offset points just past header + one 16-byte entry
        offset = struct.unpack("<I", ico[6 + 12:6 + 16])[0]
        self.assertEqual(offset, 6 + 16)
        self.assertEqual(ico[offset:], img)

    def test_group_icon_to_ico_missing_image(self):
        group = struct.pack("<HHH", 0, 1, 1) + struct.pack(
            "<BBBBHHIH", 16, 16, 0, 0, 1, 32, 10, 1)
        self.assertIsNone(exeicon._group_icon_to_ico(group, {}))  # no blobs -> None


class IconFileSafetyTest(unittest.TestCase):
    def test_missing_path(self):
        self.assertIsNone(exeicon.icon_file("Z:\\nope.exe"))
        self.assertIsNone(exeicon.icon_file(""))
        self.assertIsNone(exeicon.icon_file(None))

    def test_non_pe_file_returns_none(self):
        # a normal (non-executable) file must fail gracefully, not raise
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            f.write(b"not a real PE file")
            path = f.name
        try:
            self.assertIsNone(exeicon.icon_file(path))
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
