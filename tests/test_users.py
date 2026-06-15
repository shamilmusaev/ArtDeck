# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
from tests.helpers import write_file
from steam.users import (account_steamid64, load_users, account_name,
                         account_avatar_path, account_infos)


class UsersTest(unittest.TestCase):
    def test_steamid64_mapping(self):
        # a verified real example: uid 11111111 -> 76561197971376839
        self.assertEqual(account_steamid64("11111111"), 76561197971376839)

    def _steam_with_users(self, tmp):
        write_file(os.path.join(tmp, "config", "loginusers.vdf"),
                   '"users"\n{\n  "76561197971376839"\n  {\n'
                   '    "AccountName" "acc"\n    "PersonaName" "Player"\n  }\n}\n')

    def test_load_and_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._steam_with_users(tmp)
            users = load_users(tmp)
            self.assertEqual(users["76561197971376839"]["PersonaName"], "Player")
            self.assertEqual(account_name(tmp, "11111111"), "Player")
            self.assertIsNone(account_name(tmp, "1"))  # unknown uid -> None

    def test_avatar_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            ac = os.path.join(tmp, "config", "avatarcache")
            os.makedirs(ac)
            open(os.path.join(ac, "76561197971376839.png"), "wb").close()
            self.assertTrue(account_avatar_path(tmp, "11111111").endswith("76561197971376839.png"))
            self.assertIsNone(account_avatar_path(tmp, "1"))  # no file

    def test_account_infos(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._steam_with_users(tmp)
            infos = account_infos(tmp, ["11111111", "1"])
            self.assertEqual(infos[0], {"uid": "11111111", "name": "Player", "has_avatar": False})
            self.assertEqual(infos[1], {"uid": "1", "name": None, "has_avatar": False})


if __name__ == "__main__":
    unittest.main()
