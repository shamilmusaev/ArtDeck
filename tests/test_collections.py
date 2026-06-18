# -*- coding: utf-8 -*-
import json
import os
import tempfile
import unittest

from steam import collections

NOW = 1781400000


def _entry(cid, name, added, removed=None):
    """One [key, entry] pair the way Steam stores it."""
    key = "user-collections." + cid
    value = json.dumps({"id": cid, "name": name, "added": added,
                        "removed": removed or []}, separators=(",", ":"))
    return [key, {"key": key, "timestamp": NOW, "value": value,
                  "version": str(NOW), "conflictResolutionMethod": "custom",
                  "strMethodId": "union-collections"}]


def _namespace(pairs):
    """A compact namespace file plus some unrelated entries that must survive."""
    other_head = ["GameReleased", {"key": "GameReleased", "timestamp": 1,
                                   "value": "{}", "version": "10"}]
    other_tail = ["showcases.2", {"key": "showcases.2", "timestamp": 2,
                                  "value": "{}", "version": "11"}]
    arr = [other_head] + pairs + [other_tail]
    return json.dumps(arr, separators=(",", ":"))


def _write(tmp, text):
    path = os.path.join(tmp, "cloud-storage-namespace-1.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


class ReadTest(unittest.TestCase):
    def test_round_trip_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, _namespace([_entry("uc-gkNLyC4pZ6ge", "Epic", [12, 34])]))
            coll = collections.read_collections(path)
            self.assertEqual(coll, {"uc-gkNLyC4pZ6ge": {
                "id": "uc-gkNLyC4pZ6ge", "name": "Epic", "added": [12, 34], "removed": []}})

    def test_missing_file_returns_empty(self):
        self.assertEqual(collections.read_collections("nope.json"), {})

    def test_no_collections_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, _namespace([]))
            self.assertEqual(collections.read_collections(path), {})

    def test_garbage_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "not json at all")
            self.assertEqual(collections.read_collections(path), {})

    def test_deleted_entry_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            dead = ["user-collections.uc-dead00000000",
                    {"key": "user-collections.uc-dead00000000", "is_deleted": True}]
            path = _write(tmp, _namespace([dead]))
            self.assertEqual(collections.read_collections(path), {})


class AddTest(unittest.TestCase):
    def test_create_new_collection(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, _namespace([]))
            summary = collections.add_to_collections(path, {"GOG": [111, 222]}, now=NOW)
            self.assertEqual(summary["added"], 2)
            self.assertEqual(summary["names"], ["GOG"])
            coll = collections.read_collections(path)
            (cid, entry), = coll.items()
            self.assertTrue(cid.startswith("uc-"))
            self.assertEqual(len(cid), 15)  # "uc-" + 12 chars
            self.assertEqual(entry["id"], cid)
            self.assertEqual(entry["name"], "GOG")
            self.assertEqual(entry["added"], [111, 222])
            self.assertEqual(entry["removed"], [])

    def test_new_pair_has_steam_envelope(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, _namespace([]))
            collections.add_to_collections(path, {"Epic Games": [7]}, now=NOW)
            with open(path, "r", encoding="utf-8") as f:
                arr = json.loads(f.read())
            pair = [p for p in arr if isinstance(p[0], str)
                    and p[0].startswith("user-collections.uc-")][0]
            key, entry = pair
            self.assertEqual(entry["key"], key)
            self.assertEqual(entry["timestamp"], NOW)
            self.assertEqual(entry["version"], str(NOW))
            self.assertEqual(entry["conflictResolutionMethod"], "custom")
            self.assertEqual(entry["strMethodId"], "union-collections")

    def test_merge_into_existing_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, _namespace(
                [_entry("uc-keepThisId01", "Epic Games", [1, 2], removed=[9])]))
            summary = collections.add_to_collections(path, {"Epic Games": [2, 3, 4]}, now=NOW)
            self.assertEqual(summary["added"], 2)  # 2 already present; only 3,4 new
            coll = collections.read_collections(path)
            self.assertEqual(list(coll.keys()), ["uc-keepThisId01"])  # reused, no new id
            self.assertEqual(coll["uc-keepThisId01"]["added"], [1, 2, 3, 4])
            self.assertEqual(coll["uc-keepThisId01"]["removed"], [9])

    def test_replace_bumps_version_above_prior(self):
        # _entry stamps version == NOW; replacing must stay ahead so Steam Cloud
        # does not treat the edit as stale
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, _namespace([_entry("uc-keepThisId01", "Epic Games", [1])]))
            collections.add_to_collections(path, {"Epic Games": [2]}, now=NOW)
            arr = json.loads(open(path, "r", encoding="utf-8").read())
            entry = [e for k, e in arr if k == "user-collections.uc-keepThisId01"][0]
            self.assertEqual(int(entry["version"]), NOW + 1)

    def test_existing_with_no_new_appids_is_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = _namespace([_entry("uc-keepThisId01", "Epic Games", [1, 2])])
            path = _write(tmp, text)
            summary = collections.add_to_collections(path, {"Epic Games": [1, 2]}, now=NOW)
            self.assertEqual(summary, {"names": [], "added": 0})
            self.assertFalse(os.path.isfile(path + ".bak"))  # nothing to write
            with open(path, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), text)  # byte-for-byte unchanged

    def test_surgical_write_preserves_other_entries_and_backs_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = _namespace([_entry("uc-other00000001", "Shooter", [100])])
            path = _write(tmp, text)
            collections.add_to_collections(path, {"Epic Games": [42]}, now=NOW)
            arr = json.loads(open(path, "r", encoding="utf-8").read())
            keys = [p[0] for p in arr]
            # the unrelated entries and the pre-existing collection all survive
            self.assertIn("GameReleased", keys)
            self.assertIn("showcases.2", keys)
            self.assertIn("user-collections.uc-other00000001", keys)
            self.assertEqual(collections.read_collections(path)["uc-other00000001"]["added"], [100])
            self.assertTrue(os.path.isfile(path + ".bak"))
            with open(path + ".bak", "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), text)

    def test_two_launchers_one_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, _namespace([]))
            summary = collections.add_to_collections(
                path, {"Epic Games": [1], "GOG": [2]}, now=NOW)
            self.assertEqual(sorted(summary["names"]), ["Epic Games", "GOG"])
            self.assertEqual(summary["added"], 2)
            names = sorted(c["name"] for c in collections.read_collections(path).values())
            self.assertEqual(names, ["Epic Games", "GOG"])

    def test_noop_when_nothing_to_add(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, _namespace([]))
            summary = collections.add_to_collections(path, {}, now=NOW)
            self.assertEqual(summary, {"names": [], "added": 0})
            self.assertFalse(os.path.isfile(path + ".bak"))

    def test_missing_file_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cloud-storage-namespace-1.json")
            summary = collections.add_to_collections(path, {"Epic Games": [1]}, now=NOW)
            self.assertEqual(summary, {"names": [], "added": 0})
            self.assertFalse(os.path.isfile(path))
            self.assertFalse(os.path.isfile(path + ".bak"))


class PathTest(unittest.TestCase):
    def test_numeric_uid_guard(self):
        with self.assertRaises(ValueError):
            collections.namespace_path("C:\\Steam", "..\\..\\Windows")

    def test_path_shape(self):
        p = collections.namespace_path("C:\\Steam", "777")
        self.assertEqual(p, os.path.join("C:\\Steam", "userdata", "777", "config",
                                         "cloudstorage", "cloud-storage-namespace-1.json"))


if __name__ == "__main__":
    unittest.main()
