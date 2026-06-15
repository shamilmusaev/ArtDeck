# ArtDeck

Set SteamGridDB cover art for your Steam library, including non-Steam shortcuts, from a clean native desktop app for Windows.

> ArtDeck is not affiliated with Valve or SteamGridDB.

## Why

When you add a game to Steam as a non-Steam shortcut (a manual add, an emulator, or a launcher like Hydra), Steam usually has no 600x900 vertical cover for it, so the library shows a gray placeholder. ArtDeck fills those in, and it can also set custom art on regular installed Steam games. The interface is English by default, with a Russian toggle.

## Quick start

You need Windows, Steam, and a free SteamGridDB API key.

1. Download `ArtDeck.exe` from the [latest release](https://github.com/shamilmusaev/ArtDeck/releases/latest).
   SmartScreen may warn because the build is unsigned: click "More info", then "Run anyway". Windows 11 already includes the Edge WebView2 runtime; on Windows 10, install it if you are prompted.
2. Get an API key at [steamgriddb.com](https://www.steamgriddb.com) (Preferences > API > Generate API Key) and paste it into ArtDeck when asked. It is saved to `artdeck.key` next to the app.
3. Pick a game on the left, choose a cover, and click Apply.
4. Fully restart Steam (tray > Exit, then relaunch) so it re-reads the artwork.

Prefer running from source? Run `run_app.bat` (or `pythonw artdeck_app.py`). It installs the GUI dependencies (Pillow, pywebview) on first run.

## How to use

1. **Choose the source.** The sidebar has two tabs: Non-Steam shortcuts and installed Steam games.
2. **Find the game.** It is selected from your library automatically. Use the search box at the top to look up a different SteamGridDB entry, with live results as you type.
3. **Pick the art type.** Switch between Cover, Banner, Hero, and Logo. Turn on "Animated only" for animated covers.
4. **Preview and apply.** Hover a card for its size and style, click to preview it in the lightbox, then Apply. The art currently set in Steam is shown first, and you can restore Steam's original at any time.
5. **Bulk actions.** "Fill missing art" downloads everything missing for the account; "Remove extras" cleans up orphaned art files.
6. **Restart Steam** to see the result.

## How it works

ArtDeck reads Steam's `shortcuts.vdf` and app manifests to list your games, fetches artwork from the SteamGridDB API, and writes the images into `userdata\<id>\config\grid\`. It never modifies your Steam shortcuts, and the only network calls are to SteamGridDB. Everything runs locally.

The app is a small local HTTP server (Python standard library) that serves a vanilla HTML/CSS/JS frontend inside a native window (pywebview / Edge WebView2).

## Features

- Visual art picker: a grid of SteamGridDB variants for Cover, Banner, Hero, and Logo, with a lightbox preview.
- Two sources: Non-Steam shortcuts and installed Steam games.
- Animated covers with lightweight `.webm` previews, applied so Steam actually animates them.
- Account names and avatars instead of bare numbers, plus per-game icons in the list.
- Ambient background that eases into the selected game's palette.
- Restore original to bring back Steam's own cover.
- Auto-fill missing art and clean up orphaned files.
- Live typeahead search when auto-matching misses.
- English / Russian toggle.
- A headless CLI mode is included too.

## Build a standalone .exe

```bat
run_build.bat        :: or: python build.py
```

This produces a single `dist\ArtDeck.exe` (PyInstaller, with `web/` bundled and an icon). PyInstaller is a dev-only dependency and is installed automatically. The target machine needs the Edge WebView2 runtime (built into Windows 11). If `--onefile` misbehaves with pywebview, `build.py` has an `ONEDIR = True` fallback that builds a folder instead.

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

Offline: no network and no real Steam are required, since everything runs on temporary fixtures.

## Project layout

- `steam/`: the engine (standard library only) with modules `vdf`, `paths`, `sgdb`, `arts`, `library`, `users`, `icons`, `official`, `customimage`, `verify`.
- `artdeck_cli.py`: a thin CLI wrapper over the package.
- `artdeck_app.py`: the local HTTP server plus native window.
- `web/`: the frontend (vanilla HTML/CSS/JS, no build step) plus `i18n.js` (EN/RU).

## Privacy

- `artdeck.key` (your API key) is in `.gitignore` and is never committed.
- ArtDeck only reads `shortcuts.vdf` and app manifests, and only writes images into `userdata\<id>\config\grid\`.
- It runs locally; the only outbound traffic is to SteamGridDB to fetch art.

## License

[MIT](LICENSE)
