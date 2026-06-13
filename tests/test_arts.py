# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
from unittest.mock import patch
from steam import arts
from steam.arts import existing_art, art_status, apply_art, list_arts, fetch_art_url, ART_TYPES


class ArtsTest(unittest.TestCase):
    def test_existing_art_finds_file(self):
        with tempfile.TemporaryDirectory() as grid:
            open(os.path.join(grid, "100p.png"), "wb").close()
            self.assertTrue(existing_art(grid, 100, "p").endswith("100p.png"))
            self.assertIsNone(existing_art(grid, 100, "_hero"))

    def test_art_status_all_types(self):
        with tempfile.TemporaryDirectory() as grid:
            st = art_status(grid, 100)
            self.assertEqual(set(st.keys()), set(ART_TYPES.keys()))
            self.assertTrue(all(v is None for v in st.values()))

    def test_apply_art_removes_other_ext(self):
        with tempfile.TemporaryDirectory() as grid:
            open(os.path.join(grid, "100p.jpg"), "wb").close()

            def fake_download(url, dest):
                with open(dest, "wb"):
                    pass
            with patch("steam.arts.download", fake_download):
                dest = apply_art(grid, 100, "cover", "http://x/y.png")
            self.assertTrue(dest.endswith("100p.png"))
            self.assertFalse(os.path.isfile(os.path.join(grid, "100p.jpg")))


    def test_list_arts_sorts_cover_600x900_first(self):
        raw = [
            {"url": "u1", "thumb": "t1", "width": 1000, "height": 1500, "style": "alt"},
            {"url": "u2", "thumb": None, "width": 600, "height": 900, "style": "official"},
            {"url": None, "thumb": "t3", "width": 600, "height": 900, "style": "broken"},
        ]
        with patch("steam.arts.list_arts_raw", lambda *a, **k: raw):
            items = list_arts(123, "cover", "key")
        self.assertEqual(items[0]["url"], "u2")          # 600x900 first
        self.assertEqual(items[0]["thumb"], "u2")        # thumb falls back to url
        self.assertTrue(all(i["url"] for i in items))    # url=None item filtered out
        self.assertEqual(len(items), 2)

    def test_orientation_filter_cover_vs_banner(self):
        raw = [
            {"url": "p", "thumb": "p", "width": 600, "height": 900, "style": "s"},   # вертикальная
            {"url": "l", "thumb": "l", "width": 920, "height": 430, "style": "s"},   # горизонтальная
        ]
        with patch("steam.arts.list_arts_raw", lambda *a, **k: raw):
            cov = list_arts(1, "cover", "key")
            ban = list_arts(1, "banner", "key")
        self.assertEqual([a["url"] for a in cov], ["p"])   # обложка — только вертикальная
        self.assertEqual([a["url"] for a in ban], ["l"])   # баннер — только горизонтальная

    def test_list_arts_animated_requests_animated_type(self):
        captured = {}
        def fake_raw(endpoint, game_id, api_key, params):
            captured["params"] = dict(params)
            return [{"url": "u", "thumb": "t", "width": 600, "height": 900, "style": "s"}]
        with patch("steam.arts.list_arts_raw", fake_raw):
            items = list_arts(1, "cover", "key", animated=True)
        self.assertEqual(captured["params"]["types"], "animated")
        self.assertTrue(items and items[0]["animated"] is True)

    def test_list_arts_static_by_default(self):
        captured = {}
        def fake_raw(endpoint, game_id, api_key, params):
            captured["params"] = dict(params)
            return [{"url": "u", "thumb": "t", "width": 600, "height": 900, "style": "s"}]
        with patch("steam.arts.list_arts_raw", fake_raw):
            items = list_arts(1, "cover", "key")
        self.assertEqual(captured["params"]["types"], "static")
        self.assertFalse(items[0]["animated"])

    def test_fetch_art_url_falls_back_without_dimensions(self):
        calls = []
        def fake_raw(endpoint, game_id, api_key, params):
            calls.append(dict(params))
            if "dimensions" in params:
                return []                      # first try with dimensions -> empty
            return [{"url": "fallback"}]       # retry without dimensions -> hit
        cfg = ART_TYPES["cover"]               # cover has a "dimensions" param
        with patch("steam.arts.list_arts_raw", fake_raw):
            url = fetch_art_url(42, cfg, "key")
        self.assertEqual(url, "fallback")
        self.assertEqual(len(calls), 2)        # tried twice
        self.assertIn("dimensions", calls[0])  # first call had dimensions
        self.assertNotIn("dimensions", calls[1])  # retry dropped dimensions


if __name__ == "__main__":
    unittest.main()
