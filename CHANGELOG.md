# Changelog

All notable changes to ArtDeck are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com), and this project adheres to
[Semantic Versioning](https://semver.org).

## [Unreleased]

### Fixed

- Non-Steam game icons now show in the sidebar. They are resolved from the Steam
  `grid` folder, by extracting the icon from the game's `.exe`, or by falling back
  to cover art — previously only the shortcut's `icon` field was used, which often
  pointed at a `.exe` (unrenderable) or was empty, leaving a placeholder.
