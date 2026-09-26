# MISOL Local — repository description

## GitHub “About” description

**Experimental local receiver and logger for MISOL/Fine Offset-style Wi-Fi weather stations, with Ecowitt/Wunderground intake, SQLite, JSON/CSV, a small dashboard and optional MQTT.**

## Short version

A Windows-first, local-first weather-station receiver for compatible MISOL/Fine Offset-derived consoles. No Docker, no external database and no cloud account required for the core data path.

## What this repository is actually for

MISOL Local is a pet project for taking ownership of weather data from a compatible console without replacing the console or opening the outdoor sensor array. The console sends its normal **Customised Website** report to a small Python server on the LAN. The server stores the report in SQLite, normalises the common measurements, keeps a redacted copy of unfamiliar fields and exposes the result through a browser, JSON and CSV. 

ITS a wip Use as that.....

MQTT is available when wanted, but it is not made a compulsory dependency. Home automation is useful. Requiring somebody to build half a data centre before they can see the temperature is less useful.

The project is explicitly **experimental**. It is intended for home-lab work, protocol exploration and ordinary personal weather logging, not calibrated or safety-critical meteorology.

## Design position

The first target is the Wi-Fi console route rather than direct RF decoding. That is deliberate. A compatible console already receives the outdoor transmission and already knows how to issue Ecowitt or Weather Underground-style uploads. Reusing that observable interface keeps the original display working and avoids unnecessary hardware modification.

Later work can add RF capture, deeper Home Assistant support, forwarding and richer visualisation once real-world packet samples justify them.

## Beginner promise

The repository includes a Windows one-click launcher, setup checks, LAN-IP helper, receiver test packet, diagnostics and a literal click-by-click guide. A new user should be able to get from “I downloaded a ZIP” to “the local dashboard is listening” without Docker, Git knowledge or manual database configuration.

There will still be routers and firewalls. Software has not yet discovered a portable cure for routers and firewalls.

## Suggested GitHub topics

```text
misol
weather-station
ecowitt
fine-offset
easyweather
personal-weather-station
python
sqlite
mqtt
home-assistant
local-first
self-hosted
home-lab
```

## Ifyour looking at this as a fork or such.

> Keep the original weather console. Keep the data locally. Break as little as possible.

## Development status

**Pre-alpha / experimental.** The core parser, storage layer and HTTP receiver have automated tests, but exact field behaviour still needs validation against more physical console and firmware combinations.

## Licence

MIT. Research provenance and clean-room notes are documented in `RESEARCH.md`.
