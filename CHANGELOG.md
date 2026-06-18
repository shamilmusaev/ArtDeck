# Changelog

All notable changes to ArtDeck are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com), and this project adheres to
[Semantic Versioning](https://semver.org).

## [Unreleased]

### Added

- Imported launcher games can be dropped into a Steam library collection. A
  summary dialog before import spells out what will happen and lets you confirm or
  rename the target collection (default: the launcher name, e.g. "Epic Games"), or
  pick an existing one (suggested from your current collections). Collections are
  written surgically into the client's `cloud-storage-namespace-1.json` while Steam
  is closed, leaving every other entry untouched and backing up to `.bak`.

### Fixed

- Non-Steam game icons now show in the sidebar. They are resolved from the Steam
  `grid` folder, by extracting the icon from the game's `.exe`, or by falling back
  to cover art — previously only the shortcut's `icon` field was used, which often
  pointed at a `.exe` (unrenderable) or was empty, leaving a placeholder.
