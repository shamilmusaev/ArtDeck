# -*- coding: utf-8 -*-
import unittest
from urllib import error
import io
from steam import sgdb
from steam.sgdb import clean_name, api_get, SGDBError, SGDBAuthError


class CleanNameTest(unittest.TestCase):
    def test_strips_trademark_and_spaces(self):
        self.assertEqual(clean_name("Game™   II  "), "Game II")


class ApiGetTest(unittest.TestCase):
    def test_auth_error_raises(self):
        def fake_urlopen(req, timeout=0):
            raise error.HTTPError(req.full_url, 401, "Unauthorized", {}, io.BytesIO(b""))
        old = sgdb.request.urlopen
        sgdb.request.urlopen = fake_urlopen
        try:
            with self.assertRaises(SGDBAuthError):
                api_get("/x", "key")
        finally:
            sgdb.request.urlopen = old

    def test_404_returns_empty(self):
        def fake_urlopen(req, timeout=0):
            raise error.HTTPError(req.full_url, 404, "Not Found", {}, io.BytesIO(b""))
        old = sgdb.request.urlopen
        sgdb.request.urlopen = fake_urlopen
        try:
            self.assertEqual(api_get("/x", "key"), {"success": False, "data": []})
        finally:
            sgdb.request.urlopen = old

    def test_403_also_auth_error(self):
        def fake_urlopen(req, timeout=0):
            raise error.HTTPError(req.full_url, 403, "Forbidden", {}, io.BytesIO(b""))
        old = sgdb.request.urlopen
        sgdb.request.urlopen = fake_urlopen
        try:
            with self.assertRaises(SGDBAuthError):
                api_get("/x", "key")
        finally:
            sgdb.request.urlopen = old

    def test_retry_then_sgdb_error_on_503(self):
        calls = {"n": 0}
        def fake_urlopen(req, timeout=0):
            calls["n"] += 1
            raise error.HTTPError(req.full_url, 503, "Unavailable", {}, io.BytesIO(b""))
        old_open = sgdb.request.urlopen
        old_sleep = sgdb.time.sleep
        sgdb.request.urlopen = fake_urlopen
        sgdb.time.sleep = lambda *a, **k: None
        try:
            with self.assertRaises(SGDBError):
                api_get("/x", "key", retries=3)
            self.assertEqual(calls["n"], 3)  # все 3 попытки исчерпаны
        finally:
            sgdb.request.urlopen = old_open
            sgdb.time.sleep = old_sleep


if __name__ == "__main__":
    unittest.main()
