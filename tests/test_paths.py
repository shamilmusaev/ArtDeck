# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
from steam.paths import account_paths, list_accounts, load_api_key


class PathsTest(unittest.TestCase):
    def test_account_paths(self):
        vdf, grid = account_paths("C:\\Steam", "123")
        self.assertTrue(vdf.endswith(os.path.join("userdata", "123", "config", "shortcuts.vdf")))
        self.assertTrue(grid.endswith(os.path.join("userdata", "123", "config", "grid")))

    def test_list_accounts_finds_vdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = os.path.join(tmp, "userdata", "999", "config")
            os.makedirs(cfg)
            open(os.path.join(cfg, "shortcuts.vdf"), "wb").close()
            self.assertEqual(list_accounts(tmp), ["999"])

    def test_load_api_key_from_env(self):
        os.environ["STEAMGRIDDB_API_KEY"] = "  abc123  "
        try:
            self.assertEqual(load_api_key(None), "abc123")
        finally:
            del os.environ["STEAMGRIDDB_API_KEY"]


if __name__ == "__main__":
    unittest.main()
