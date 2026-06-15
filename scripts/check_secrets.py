#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail if any git-tracked file leaks a secret or personal data.

Run by the pre-commit hook (.githooks/pre-commit) and by the test suite
(tests/test_no_secrets.py). Standard library only, no dependencies.

Catches the classes of leak that have actually bitten this project:
  - artdeck.key (the SteamGridDB API key) accidentally tracked (e.g. git add -f)
  - a LIVE SteamID64 (7656119[89]xxxxxxxxx) -> links to a real Steam profile;
    synthetic test ids (765611979...) are intentionally allowed
  - absolute Windows user/dev paths (C:\\Users\\..., X:\\Apps\\...)
  - email addresses outside obvious project/test domains
  - the previous author handle 'sammaxwell'

Exit code 0 = clean, 1 = leak found (and printed to stderr).
"""
import os
import re
import subprocess
import sys

# This scanner and its test necessarily contain the patterns themselves.
SELF = {"scripts/check_secrets.py", "tests/test_no_secrets.py"}
SKIP_EXT = {".png", ".jpg", ".jpeg", ".webp", ".ico", ".gif", ".webm", ".bin", ".exe"}
# evil.com / example.com are deliberate test/example strings (URL-spoofing tests).
ALLOWED_EMAIL_DOMAINS = ("steamgriddb.com", "github.com", "example.com", "evil.com")

PATTERNS = [
    (re.compile(r"7656119[89]\d{9}"), "live SteamID64"),
    (re.compile(r"[A-Za-z]:\\Users\\", re.I), "absolute Windows user path"),
    (re.compile(r"[A-Za-z]:\\Apps\\", re.I), "absolute dev path"),
    (re.compile(r"sammaxwell", re.I), "old author handle"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "email address"),
]


def tracked_files():
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout
    return [f for f in out.splitlines() if f]


def scan():
    hits = []
    for path in tracked_files():
        if os.path.basename(path) == "artdeck.key":
            hits.append((path, 0, "forbidden file tracked", path))
            continue
        if path in SELF or os.path.splitext(path)[1].lower() in SKIP_EXT:
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            for rx, label in PATTERNS:
                m = rx.search(line)
                if not m:
                    continue
                if label == "email address" and m.group(0).split("@")[1].lower() in ALLOWED_EMAIL_DOMAINS:
                    continue
                hits.append((path, i, label, m.group(0)))
    return hits


def main():
    hits = scan()
    if hits:
        sys.stderr.write("SECRET / PII scan FAILED:\n")
        for path, ln, label, snippet in hits:
            sys.stderr.write("  %s:%d  [%s]  %s\n" % (path, ln, label, snippet))
        sys.stderr.write("\nRemove the data (or use a synthetic test fixture) before committing.\n")
        return 1
    print("secret/PII scan: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
