# Changelog

## 0.1.1-dev

Beginner-facing packaging pass.

- rewrote `README.md` as a Windows-first setup and operating guide
- expanded `DESCRIPTION.md` for GitHub use
- added `docs/IDIOTS-GUIDE-WINDOWS.md`
- added root-level one-click Windows launchers
- hardened the Windows setup script with a Python version check
- setup now runs the built-in tests before declaring success
- added LAN-IP helper and Windows diagnostics
- added a local fake-weather packet test utility
- added a Linux setup helper without introducing Docker
- retained the explicit experimental and clean-room status

## 0.1.0-dev

Initial experimental clean-room build.

- local Ecowitt/Wunderground receiver
- SQLite storage
- metric normalisation
- redacted raw payload retention
- JSON, CSV and HTML read-back
- optional MQTT output
- Windows helper scripts
- protocol/storage tests
