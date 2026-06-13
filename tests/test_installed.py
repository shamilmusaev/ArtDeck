# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
from tests.helpers import write_file, make_library
from steam.library import list_libraries, load_installed, STEAM_TOOL_APPIDS


class InstalledTest(unittest.TestCase):
    def _steam(self, tmp, libs):
        # libs: list of (relpath, {appid:name}); rel "" means the steam root itself
        entries = []
        for i, (rel, apps) in enumerate(libs):
            root = os.path.join(tmp, rel) if rel else tmp
            make_library(root, apps)
            entries.append('  "%d"\n  {\n    "path" "%s"\n  }\n'
                           % (i, root.replace("\\", "\\\\")))
        write_file(os.path.join(tmp, "steamapps", "libraryfolders.vdf"),
                   '"libraryfolders"\n{\n%s}\n' % "".join(entries))
        return tmp

    def test_list_libraries(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._steam(tmp, [("", {"431960": "Wallpaper Engine"}),
                              ("L2", {"8870": "BioShock"})])
            libs = list_libraries(tmp)
            self.assertIn(tmp, libs)
            self.assertIn(os.path.join(tmp, "L2"), libs)

    def test_load_installed_filters_tools_and_dedups(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._steam(tmp, [
                ("", {"431960": "Wallpaper Engine", "228980": "Steamworks Common Redistributables"}),
                ("L2", {"8870": "BioShock Infinite", "1493710": "Proton 8.0"}),
            ])
            games = load_installed(tmp)
            names = sorted(g["name"] for g in games)
            self.assertEqual(names, ["BioShock Infinite", "Wallpaper Engine"])
            self.assertTrue(all(g["kind"] == "steam" for g in games))
            self.assertTrue(all(isinstance(g["appid"], int) for g in games))
            self.assertIn(228980, STEAM_TOOL_APPIDS)


if __name__ == "__main__":
    unittest.main()
