# MISOL Local

> **EXPERIMENTAL side project.** MISOL Local is not an official MISOL, Fine Offset, Ecowitt, Weather Underground or Home Assistant project. Its a small clean-room receiver built for tinkering with a compatible weather-station console on a local network. WIP

MISOL Local catches the weather reports that a compatible Wi-Fi console would normally send to a remote weather service, stores a local copy, and gives you a simple browser view, JSON output, CSV export and optional MQTT publishing.

my design choice is to leave the outdoor station alone. No soldering iron, no replacement display, no 11pm heroic attempt to improve a waterproof sensor with a screwdriver at 2am after i get siede tracked playing KingShot. The console already knows how to send data to a customised server, so this project starts there.

**Windows is the first-class beginner route. Docker is not required.** The core receiver uses the Python standard library and SQLite, so there is no separate database server to install.


## I added a simple guide.
## Start here if you have never used Python

If the words *virtual environment*, *localhost* or *HTTP POST* mean very little to you, that is fine. Use the one-click route below and ignore the developer sections until you actually need them.

### What you need

You need:

- a Windows 10 or Windows 11 PC on the same home network as the weather console;
- Python **3.11 or newer**;
- this repository downloaded and extracted to an ordinary folder;
- the weather console powered from its mains adaptor so its Wi-Fi remains active;
- access to the console's **Customised Website** upload settings, normally through WS View or the relevant companion app.

You do **not** need Docker, MySQL, a Raspberry Pi, Home Assistant, an MQTT broker or a degree in pretending YAML is a personality.

### 1. Download and extract the project

Download the ZIP from GitHub and extract it somewhere sensible, for example:

```text
C:\Users\YourName\Documents\misol-local\
```

Do not run it from inside the ZIP preview. Windows will let you try. Windows also lets you put files on the desktop until the desktop becomes an archaeological layer. Neither habit helps debugging.

### 2. Install Python

Install Python **3.11 or newer** from the official Python website.

During installation, tick:

```text
Add python.exe to PATH
```

If you forget that box, the project will not be able to find Python from a normal command window. Re-running the Python installer and choosing **Modify** is usually the easiest fix.

### 3. Double-click the beginner launcher

From the project folder, double-click:

```text
START-HERE-WINDOWS.bat
```

The launcher will:

1. check that a suitable Python version exists;
2. create a private Python environment inside `.venv`;
3. install MISOL Local;
4. install the optional MQTT library;
5. create `config.ini` from the supplied example if it does not already exist;
6. start the receiver;
7. open the dashboard in your browser.

The first setup can take a minute or two because Python may need to download packaging files. Later starts are quicker.

If Windows Firewall asks whether Python may accept connections, allow it on **Private networks**. Do not enable Public networks unless you have a specific reason and understand why.

### 4. Check the local dashboard

The browser should open:

```text
http://127.0.0.1:8080/
```

At first it will probably say that there are no readings. That is correct. The receiver is running, but the weather console has not been told where to send anything yet.

You can also check:

```text
http://127.0.0.1:8080/health
```

A healthy receiver returns JSON showing that the service and database are alive.

### 5. Find this PC's network address

Double-click:

```text
GET-MY-IP-WINDOWS.bat
```

It will show the useful IPv4 addresses Windows can find. You are normally looking for something like:

```text
192.168.1.42
```

or:

```text
192.168.0.42
```

The exact number depends on your router.

**Do not put `127.0.0.1` into the weather console.** That address means “this device itself”. On the console, it would point back at the console rather than at your PC. !!!!!!!

### 6. Point the weather console at MISOL Local

Open the console's custom upload settings. The wording changes slightly between firmware and app versions, but for the common EasyWeather/Ecowitt-style interface start with:

```text
Customised Website: Enabled
Protocol type:       Ecowitt
Server IP/Hostname:  <your PC's IPv4 address>
Path:                /data/report/
Port:                8080
Upload interval:     16 seconds
```

Example:

```text
Server IP/Hostname:  192.168.1.42
Path:                /data/report/
Port:                8080
```

Save the settings.

Ecowitt mode is the preferred starting point because these consoles commonly expose more fields in that format. MISOL Local also accepts the older Weather Underground-style endpoint:

```text
/weatherstation/updateweatherstation.php
```

### 7. Wait for a reading

Give it roughly one or two reporting intervals. Then refresh:

```text
http://127.0.0.1:8080/
```

A successful first report should appear as a station card with normalised values.

Useful endpoints are:

| Address | What it does |
| --- | --- |
| `/` | small local dashboard |
| `/health` | service and database health |
| `/api/latest` | latest observation per station |
| `/api/recent?limit=100` | recent observations |
| `/export.csv?limit=1000` | CSV export |
| `/data/report/` | Ecowitt-style receiver |
| `/weatherstation/updateweatherstation.php` | Wunderground-style receiver |

## Test it before touching the weather console

You can prove the software works with a fake weather report first.

Keep MISOL Local running, then double-click:

```text
TEST-RECEIVER-WINDOWS.bat
```

The test utility sends a harmless sample observation to the local receiver. Refresh the dashboard afterwards. If the sample appears, the Python receiver and SQLite database are working and any remaining problem is between the console, Wi-Fi and Windows Firewall.

That distinction saves a surprising amount of random clicking.

## If something goes wrong

Run:

```text
DIAGNOSE-WINDOWS.bat
```

It checks the common local problems: Python, the virtual environment, configuration, whether port 8080 appears to be listening, and whether the local health endpoint responds.

The most common failures are less exotic than people hope:

| Symptom | Likely cause | What to check |
| --- | --- | --- |
| `START-HERE-WINDOWS.bat` says Python is missing | Python is not installed or is not on PATH | Install Python 3.11+ and tick **Add python.exe to PATH** |
| Dashboard opens but stays empty | Console is not reaching the PC | PC IP, port 8080, protocol, path and firewall |
| Test packet works but real station does not | Receiver is fine, network/configuration is not | Use the PC's LAN IP, not `127.0.0.1`; confirm both devices are on the same LAN |
| Console refuses Wi-Fi | Many of these consoles use 2.4 GHz Wi-Fi | Check the router has 2.4 GHz enabled and the console can join it |
| Browser says port already in use | Another program already owns port 8080 | Change the port in `config.ini`, then use the same port in the console |
| MQTT errors appear | MQTT was enabled without a reachable broker | Disable MQTT in `config.ini` until the basic receiver works |
| Data values look odd | Firmware field/unit variation or calibration | Keep the raw payload, compare against the console and report the packet |

For a more literal click-by-click walkthrough, see [`docs/IDIOTS-GUIDE-WINDOWS.md`](docs/IDIOTS-GUIDE-WINDOWS.md). The filename is intentionally blunt; the instructions are not.

## Stopping and restarting it

The black terminal window is the running receiver.

To stop it cleanly, click that window and press:

```text
Ctrl+C
```

To run it again later, double-click:

```text
RUN-MISOL-LOCAL-WINDOWS.bat
```

You do not need to repeat the full setup every time.

## Where your data lives

By default the SQLite database is:

```text
data\misol.sqlite3
```

That single file contains the stored observations. To make a basic backup, stop MISOL Local and copy that file somewhere safe.

The database keeps two versions of useful information:

1. **normalised values**, with common temperature, pressure, rain and wind fields converted to a compact metric model;
2. **redacted raw fields**, so unfamiliar firmware fields are not discarded before we know what they mean.

Credential-like fields such as `PASSKEY`, passwords, tokens and station keys are redacted from the stored raw payload. A station with a `PASSKEY` gets a repeatable local fingerprint derived from a hash rather than the key being stored as its identifier.

## Configuration

The setup script creates:

```text
config.ini
```

from:

```text
config.example.ini
```

The default configuration is deliberately small:

```ini
[server]
host = 0.0.0.0
port = 8080
database = data/misol.sqlite3
max_recent = 1000

[privacy]
store_raw = yes
redact_keys = PASSKEY,PASSWORD,password,stationkey,station_key,key,token,secret

[mqtt]
enabled = no
host = 127.0.0.1
port = 1883
topic_prefix = misol-local
username =
password =
retain = no
```

`0.0.0.0` means “listen on the machine's available network interfaces”. That is what lets the weather console reach the receiver from another device on your LAN.

## MQTT, later

MQTT is optional. Get ordinary receiving working before enabling it.

When you do want MQTT, edit `config.ini`:

```ini
[mqtt]
enabled = yes
host = 192.168.1.20
port = 1883
topic_prefix = misol-local
username =
password =
retain = no
```

Each observation is published as one JSON object to:

```text
misol-local/<station-id>/state
```

The project uses `paho-mqtt` only for this optional output. The Windows setup installs it, but leaving MQTT disabled means no broker is required.

## What MISOL Local currently understands

The parser is intentionally tolerant. It recognises common Ecowitt and Weather Underground custom-upload fields for:

- indoor and outdoor temperature;
- indoor and outdoor humidity;
- relative and absolute pressure;
- wind direction;
- wind speed and gusts;
- rain rate and accumulated rainfall periods;
- solar radiation;
- UV index;
- a selection of battery fields;
- station metadata where supplied.

Unknown fields remain in the redacted raw payload rather than being deleted or confidently “decoded” by wishful thinking.

## Why this approach

The target console family already supports a **Customised Website** upload. That gives us a clean interception point:

```text
Outdoor sensor array
        |
        | 433/868 MHz, model dependent
        v
Original MISOL/Fine Offset-style console
        |
        | local Wi-Fi HTTP upload
        v
MISOL Local
        |
        +--> SQLite
        +--> browser / JSON / CSV
        +--> MQTT, if enabled
```

It preserves the original screen and weather hardware. RF decoding can still be explored later, but it is no longer a prerequisite for owning your own data.

## Project layout

```text
misol-local/
|-- START-HERE-WINDOWS.bat          beginner setup + run
|-- RUN-MISOL-LOCAL-WINDOWS.bat     normal later starts
|-- GET-MY-IP-WINDOWS.bat           shows likely LAN addresses
|-- TEST-RECEIVER-WINDOWS.bat       sends a local test observation
|-- DIAGNOSE-WINDOWS.bat            basic Windows diagnostics
|-- README.md
|-- DESCRIPTION.md
|-- EXPERIMENTAL.md
|-- RESEARCH.md
|-- ROADMAP.md
|-- config.example.ini
|-- pyproject.toml
|-- misol_local/
|   |-- __main__.py
|   |-- config.py
|   |-- protocol.py
|   |-- server.py
|   |-- storage.py
|   `-- mqtt.py
|-- tools/
|   `-- send_test_packet.py
|-- scripts/
|   |-- setup_windows.bat
|   |-- run_windows.bat
|   |-- run_windows_debug.bat
|   |-- diagnose_windows.bat
|   |-- get_ip_windows.bat
|   |-- test_receiver_windows.bat
|   |-- setup_linux.sh
|   `-- run_linux.sh
|-- docs/
|   `-- IDIOTS-GUIDE-WINDOWS.md
`-- tests/
```

## Linux quick start

Linux is supported, but Windows is the route being polished first.

```bash
chmod +x scripts/setup_linux.sh scripts/run_linux.sh
./scripts/setup_linux.sh
./scripts/run_linux.sh
```

Then browse to:

```text
http://127.0.0.1:8080/
```

On a Linux machine used as a permanent receiver, a proper service unit is sensible later. It is deliberately not forced into the first release because “just add systemd, Docker, reverse proxying and TLS” is how a ten-minute pet project becomes an unpaid infrastructure department.

## Developer setup

Create and activate a virtual environment, then install the project in editable mode:

```bash
python -m venv .venv
```

Windows:

```text
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install -r requirements-optional.txt
```

Run:

```bash
python -m misol_local --config config.ini
```

Debug logging:

```bash
python -m misol_local --config config.ini --debug
```

Tests:

```bash
python -m unittest discover -s tests -v
```

The current tests cover protocol detection, representative Ecowitt normalisation, malformed numeric input, SQLite round-tripping and an actual local HTTP POST through the receiver.

## Experimental status

This project is **pre-alpha**. It has automated tests and a defined data path, but the target is real consumer weather hardware with firmware variants in circulation. That means a physically captured packet from a particular console can still expose fields, units or edge cases that are not represented in the test fixtures.

Do not use MISOL Local as the sole source for safety-critical weather decisions, flood warnings, aviation, scientific calibration or anything else where “the hobby server seems fine” is not a suitable assurance case. You use o your own ass. its a pet side pproject and wip.

See [`EXPERIMENTAL.md`](EXPERIMENTAL.md) for the deliberately boring version of that warning.

## Clean-room development and research provenance

MISOL Local was written from scratch after surveying public MISOL, EasyWeather, Fine Offset and Ecowitt-related projects to understand observable behaviour, protocol conventions, useful failure cases and sensible integration patterns.

Implementation code from repositories without a compatible licence was not copied into this project. Projects with permissive licences were still treated as research references rather than as source files to transplant. `RESEARCH.md` records the projects surveyed and the design lessons taken from them..

That is slightlyy more paperwork than a pet weather receiver strictly needs, but it is cheaper than discovering six months later that nobody remembers which three lines came from where. Trust me here we have all been there.....

## Contributing

Useful contributions are currently very practical:

- anonymised raw payload samples from compatible consoles;
- confirmation of firmware/model combinations;
- tests for odd fields or units;
- Windows setup failures with the exact error text;
- Home Assistant/MQTT validation;
- documentation fixes from people who actually followed the beginner guide rather than merely admiring it.

Do not include real station passwords, API keys, private IP screenshots containing unrelated sensitive information, or cloud-service credentials in issues. I know is hould not have to say this but also im aware we all start somewhere.

## Licence

MISOL Local is released under the **MIT Licence**. See [`LICENSE`](LICENSE).
