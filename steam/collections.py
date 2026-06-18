# -*- coding: utf-8 -*-
"""Read and write Steam library collections.

The modern Steam client keeps user collections in
userdata/<uid>/config/cloudstorage/cloud-storage-namespace-1.json (NOT in
localconfig.vdf's "user-collections" key, which this build leaves empty). The
file is a compact JSON array of [key, entry] pairs; each collection is one pair

    ["user-collections.<id>", {"key":"user-collections.<id>","timestamp":<unix>,
     "value":"<escaped-json of {id,name,added,removed}>","version":"<unix>",
     "conflictResolutionMethod":"custom","strMethodId":"union-collections"}]

When ArtDeck imports launcher games it can drop each one into a collection named
after its launcher, so the library stays tidy.

The write is surgical: we add ONE new pair (or replace ONE existing pair when a
collection of that name already exists) and leave every other pair byte-for-byte
intact, so we never disturb the user's other ~200 entries (playtime rollups,
showcases, other collections). Steam must be closed first - it rewrites this
file on exit, so hot edits are lost; the import flow already closes Steam, and we
write before it relaunches. We back up to .bak and replace atomically. Editing
this file while Steam is closed is what BoilR / Steam ROM Manager do (the user's
own srm-* collections prove it); it touches only a local config file, never a
game process or the network.
"""
import json
import os
import secrets
import shutil
import time

_PREFIX = "user-collections."
_ID_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def namespace_path(steam_path, uid):
    """Path to an account's collections store. The uid is always a numeric Steam
    account id; reject anything else so a crafted value can't traverse out of
    userdata (mirrors account_paths in steam/paths.py)."""
    if not str(uid).isdigit():
        raise ValueError("invalid account id")
    return os.path.join(steam_path, "userdata", uid, "config", "cloudstorage",
                        "cloud-storage-namespace-1.json")


def _new_id():
    """A fresh collection id: "uc-" + 12 base62 chars (matches Steam's form)."""
    return "uc-" + "".join(secrets.choice(_ID_ALPHABET) for _ in range(12))


def _read_text(path):
    """The namespace file as text, or "" if missing/unreadable (degrade gracefully)."""
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def _parse_pairs(text):
    """The [key, entry] pairs, or [] if the file is not a JSON array."""
    try:
        data = json.loads(text)
    except Exception:
        return []
    return data if isinstance(data, list) else []


def _iter_collection_pairs(pairs):
    """Yield (key, entry, coll) for every live collection pair, applying the five
    structural guards (pair shape, key prefix, non-deleted dict entry, string
    value, parseable JSON). Shared by read_collections and add_to_collections so
    the guard logic lives in one place."""
    for pair in pairs:
        if not (isinstance(pair, list) and len(pair) == 2):
            continue
        key, entry = pair
        if not (isinstance(key, str) and key.startswith(_PREFIX)):
            continue
        if not isinstance(entry, dict) or entry.get("is_deleted"):
            continue
        value = entry.get("value")
        if not isinstance(value, str):
            continue
        try:
            coll = json.loads(value)
        except Exception:
            continue
        if isinstance(coll, dict):
            yield key, entry, coll


def read_collections(path):
    """All collections as {id: {"id","name","added","removed"}}, or {} if the
    file is absent/unparseable. Deleted entries (is_deleted) are skipped."""
    out = {}
    for key, entry, coll in _iter_collection_pairs(_parse_pairs(_read_text(path))):
        if isinstance(coll.get("id"), str):
            out[coll["id"]] = coll
    return out


def _bracket_end(text, start):
    """Index just past the bracket that opens at text[start] (a '[' or '{'),
    respecting JSON string literals and escapes. -1 if unbalanced."""
    depth = 0
    in_str = False
    esc = False
    i = start
    n = len(text)
    while i < n:
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "[" or c == "{":
            depth += 1
        elif c == "]" or c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def _pair_text(key, coll, now, version):
    """Serialize one [key, entry] pair the way Steam stores it (compact, exact
    field order). value is the collection re-encoded as an escaped JSON string.
    `version` is the conflict-resolution counter (kept ahead of any prior value so
    Steam Cloud does not treat our edit as stale)."""
    value = json.dumps(coll, separators=(",", ":"), ensure_ascii=False)
    entry = {
        "key": key,
        "timestamp": now,
        "value": value,
        "version": str(version),
        "conflictResolutionMethod": "custom",
        "strMethodId": "union-collections",
    }
    return json.dumps([key, entry], separators=(",", ":"), ensure_ascii=False)


def _insert_pair(text, pair_text):
    """Append a pair before the array's closing ']', preserving all other bytes."""
    i = text.rindex("]")
    before = text[:i].rstrip()
    tail = text[i:]
    if before.endswith("["):  # empty array []
        return before + pair_text + tail
    return before + "," + pair_text + tail


def _replace_pair(text, key, pair_text):
    """Replace the existing pair whose key matches, byte-for-byte elsewhere.
    Returns None if the key is not found in the raw text."""
    needle = '["' + key + '"'
    idx = text.find(needle)
    if idx < 0:
        return None
    end = _bracket_end(text, idx)
    if end < 0:
        return None
    return text[:idx] + pair_text + text[end:]


def add_to_collections(path, groups, now=None):
    """Merge appids into collections named by `groups` ({name: [appids]}).

    For each name, reuse an existing collection that matches by name (case
    sensitive, the way Steam shows it) else create one with a fresh id; append
    the new appids to "added" (deduped, order preserved). The matching pair is
    surgically replaced (or a new pair appended) in the raw file; every other
    pair is left untouched. Backs up to .bak and writes atomically. Returns a
    summary {"names": [...], "added": <count>}; a no-op (empty summary, no write)
    if there is nothing to add or the file is missing/unparseable."""
    groups = {name: list(ids) for name, ids in (groups or {}).items() if name and ids}
    if not groups:
        return {"names": [], "added": 0}
    if now is None:
        now = int(time.time())

    text = _read_text(path)
    pairs = _parse_pairs(text)
    if not text or not pairs:
        # No store (or unreadable/empty): nothing safe to surgically edit.
        return {"names": [], "added": 0}

    # Map collection name -> (key, collection dict) from the existing entries.
    by_name = {}
    for key, entry, coll in _iter_collection_pairs(pairs):
        if isinstance(coll.get("name"), str):
            by_name.setdefault(coll["name"], (key, coll, entry.get("version")))

    names_touched = []
    total_added = 0
    for name, appids in groups.items():
        existing = by_name.get(name)
        if existing is None:
            cid = _new_id()
            key = _PREFIX + cid
            coll = {"id": cid, "name": name, "added": [], "removed": []}
            version = now
        else:
            key, coll, prev_version = existing
            # stay ahead of the prior (possibly cloud-synced) version so Steam's
            # conflict resolution does not discard our merged appids as stale
            try:
                version = max(now, int(prev_version) + 1)
            except (TypeError, ValueError):
                version = now

        added = coll.get("added")
        if not isinstance(added, list):
            added = []
        seen = set(added)
        n_before = total_added
        for aid in appids:
            if aid not in seen:
                added.append(aid)
                seen.add(aid)
                total_added += 1
        coll["added"] = added
        coll.setdefault("removed", [])
        coll["id"] = key[len(_PREFIX):]
        coll["name"] = name

        if total_added == n_before and existing is not None:
            continue  # nothing new for an already-present collection; leave it

        pair_text = _pair_text(key, coll, now, version)
        if existing is None:
            text = _insert_pair(text, pair_text)
            # a later group with the same name reuses this pair (and bumps version)
            by_name[name] = (key, coll, str(version))
        else:
            replaced = _replace_pair(text, key, pair_text)
            if replaced is None:
                continue
            text = replaced
        names_touched.append(name)

    if not names_touched:
        return {"names": [], "added": total_added}

    _write_atomic(path, text)
    return {"names": names_touched, "added": total_added}


def _write_atomic(path, new_text):
    """Back up the namespace file to .bak, then write new_text atomically. Raises
    if the backup fails - never risk the only copy of the user's collections."""
    backup = path + ".bak"
    shutil.copy2(path, backup)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(new_text)
    os.replace(tmp, path)
    return backup
