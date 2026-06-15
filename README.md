# ArtDeck

**Cover art for your Steam library.** ArtDeck pulls artwork (covers, banners, heroes,
logos) from [SteamGridDB](https://www.steamgriddb.com) and drops it into Steam — in one click.

> ⚠️ ArtDeck is **not affiliated** with Valve or SteamGridDB.

Why: when you add a game to Steam as a **non-Steam shortcut** (manual add, emulators,
third-party launchers like Hydra), Steam often gets no 600×900 vertical cover — leaving a
gray placeholder in the library. ArtDeck fixes that, and also lets you set **custom** art on
regular installed Steam games.

The UI ships in **English by default** with a **Russian** toggle.

## Quick start

Requires **Python 3.x** (Windows) and Steam.

1. Get a free SteamGridDB API key:
   [steamgriddb.com](https://www.steamgriddb.com) → Preferences → API → *Generate API Key*.
   Paste it into the app (the key button) — it's saved to `artdeck.key`.
   (Or set the `STEAMGRIDDB_API_KEY` environment variable.)
2. Run **`run_app.bat`** (or `pythonw artdeck_app.py`) — it installs the GUI deps
   (Pillow, pywebview) on first run and opens the native ArtDeck window.

After applying art, **fully restart Steam** (tray → Exit, then relaunch) so it re-reads the
grid folder.

## Features

- 🖼️ **Visual art picker** — a grid of SteamGridDB variants across 4 types
  (cover, banner, hero, logo), with a lightbox preview.
- 🎮 **Two tabs** — **Non-Steam** shortcuts and **Installed** Steam games.
- 🎞️ **Animated covers** — an "animated only" filter with lightweight `.webm` previews;
  applied with the registration Steam needs to actually animate them.
- 👤 **Account names & avatars** (not bare numbers), plus per-game icons in the list.
- 🌈 **Ambient background** that eases into the selected game's palette.
- ↺ **Restore original** — remove your art and bring back Steam's own cover.
- ⚡ **Auto-fill** missing art and 🧹 **clean up** orphaned art files.
- 🔎 **Manual search** when auto-matching misses.
- 🌍 **EN / RU** language toggle.
- 💻 A headless **CLI** mode is included too.

## Build a standalone .exe

```bat
run_build.bat        :: or: python build.py
```

Produces a single `dist\ArtDeck.exe` (PyInstaller, with `web/` bundled and an icon).
PyInstaller is a dev-only dependency and is installed automatically. The target machine
needs the **Edge WebView2** runtime (built into Windows 11). If `--onefile` misbehaves with
pywebview, `build.py` has an `ONEDIR = True` fallback (folder build).

## CLI (no GUI)

```bat
python artdeck_cli.py                 :: fill missing art across all accounts
python artdeck_cli.py --dry-run       :: show the plan, download nothing
python artdeck_cli.py --types cover   :: covers only
python artdeck_cli.py --clean         :: delete orphaned art
python artdeck_cli.py --account <uid> :: a single account
python artdeck_cli.py --force         :: overwrite existing art
```

## Tests

```bat
python -m unittest discover -t . -s tests -v
```

Offline — no network and no real Steam required (everything runs on temp fixtures).

## How it works

- **`steam/`** — the engine (stdlib-only): `vdf` · `paths` · `sgdb` · `arts` · `library` ·
  `users` · `icons` · `official` · `customimage` · `verify`.
- **`artdeck_cli.py`** — a thin CLI wrapper over the package.
- **`artdeck_app.py`** — a local HTTP server + native window (pywebview).
- **`web/`** — the frontend (vanilla HTML/CSS/JS, no build step) + `i18n.js` (EN/RU).

## Security & privacy

- `artdeck.key` (your API key) is in `.gitignore` and never committed.
- ArtDeck only **reads** `shortcuts.vdf` / app manifests and **writes** images into
  `userdata\<uid>\config\grid\` — it does not modify your Steam shortcuts.
- It runs locally; the only network calls are to SteamGridDB to fetch art.

## License

[MIT](LICENSE) © 2026 shamilmusaev
