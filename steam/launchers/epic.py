# -*- coding: utf-8 -*-
"""Detect installed Epic Games Store games from its manifest files.

Epic writes one JSON .item per installed app under
%PROGRAMDATA%\\Epic\\EpicGamesLauncher\\Data\\Manifests. We read DisplayName +
InstallLocation + LaunchExecutable and skip DLC / non-application entries."""
import json
import os


def _default_dir():
    base = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    return os.path.join(base, "Epic", "EpicGamesLauncher", "Data", "Manifests")


def detect(manifests_dir=None):
    """[{"name","exe","start_dir","launcher":"epic"}] for installed Epic games.
    A bad/partial manifest is skipped, not fatal."""
    d = manifests_dir or _default_dir()
    if not os.path.isdir(d):
        return []
    games = []
    for fn in sorted(os.listdir(d)):
        if not fn.lower().endswith(".item"):
            continue
        try:
            with open(os.path.join(d, fn), encoding="utf-8") as f:
                m = json.load(f)
        except Exception:
            continue
        name = m.get("DisplayName") or ""
        loc = m.get("InstallLocation") or ""
        launch = m.get("LaunchExecutable") or ""
        if not (name and loc and launch) or not m.get("bIsApplication", True):
            continue
        exe = os.path.normpath(os.path.join(loc, launch))
        games.append({"name": name, "exe": exe, "start_dir": loc, "launcher": "epic"})
    return games
