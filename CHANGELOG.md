# Changelog

## 0.3.0-dev

Experimental research and reliability update.

Added Open-Meteo current conditions as a second general reference source alongside OpenWeather and satellite solar radiation. Added provider health state, latency tracking and isolated provider failures.

Added weather quality-control flags for broad plausibility, rapid temporal changes and internal wind consistency. Added an optional derived-stream safety valve for physically impossible values while preserving raw history.

Added historical calibration learning based on agreement between at least two external references. Calibration uses median bias and median absolute deviation, retains provenance, and does not alter the best-estimate stream unless explicitly enabled.

Added calibration storage, API reporting, SQLite migration support, request size limits, response security headers and expanded MQTT metadata.

Replaced the release-triggered PyPI publishing workflow with test-only CI for Windows and Ubuntu across supported Python versions.

Expanded clean-room research notes and tests.

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
