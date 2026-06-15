# -*- coding: utf-8 -*-
"""Guardrail: no secret or personal data may live in tracked files.

Runs the repo's secret scanner as part of the normal test suite, so a leak
(real SteamID64, API key, personal path, email, old author handle) fails CI/tests
just like any other bug. See scripts/check_secrets.py.
"""
import os
import subprocess
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class NoSecretsTest(unittest.TestCase):
    def test_no_secrets_or_pii_in_tracked_files(self):
        scanner = os.path.join(REPO, "scripts", "check_secrets.py")
        if not os.path.isfile(scanner):
            self.skipTest("scanner missing")
        r = subprocess.run([sys.executable, scanner], cwd=REPO,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0,
                         "secret/PII scan failed:\n" + r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
