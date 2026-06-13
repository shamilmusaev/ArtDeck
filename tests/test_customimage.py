# -*- coding: utf-8 -*-
import json
import os
import tempfile
import unittest
from steam.customimage import register_custom_image


class CustomImageTest(unittest.TestCase):
    def _read(self, steam, uid, appid):
        p = os.path.join(steam, "userdata", str(uid), "config", "librarycache", "%d.json" % appid)
        with open(p, encoding="utf-8") as f:
            return json.load(f)

    def test_creates_registration_when_absent(self):
        with tempfile.TemporaryDirectory() as steam:
            register_custom_image(steam, "999", 2468090731)
            arr = self._read(steam, "999", 2468090731)
            ci = dict((k, v) for k, v in arr)["customimage"]
            self.assertTrue(ci["data"])              # непустой data — это и включает арт
            self.assertEqual(ci["data"]["nVersion"], 1)

    def test_preserves_other_entries_and_existing_logo(self):
        with tempfile.TemporaryDirectory() as steam:
            lc = os.path.join(steam, "userdata", "999", "config", "librarycache")
            os.makedirs(lc)
            existing = [
                ["achievements", {"version": 2, "data": {"nTotal": 5}}],
                ["customimage", {"version": 1, "data": {"nVersion": 1,
                    "logoPosition": {"pinnedPosition": "TopRight", "nWidthPct": 30, "nHeightPct": 40}}}],
            ]
            with open(os.path.join(lc, "55.json"), "w", encoding="utf-8") as f:
                json.dump(existing, f)
            register_custom_image(steam, "999", 55)
            arr = self._read(steam, "999", 55)
            d = dict((k, v) for k, v in arr)
            self.assertIn("achievements", d)                      # чужая запись сохранена
            self.assertEqual(d["achievements"]["data"]["nTotal"], 5)
            self.assertEqual(d["customimage"]["data"]["logoPosition"]["pinnedPosition"], "TopRight")  # позиция лого сохранена


if __name__ == "__main__":
    unittest.main()
