# MISOL Local: the idiot's guide to Windows setup

This is the version for somebody who wants the weather station working and does not particularly want a surprise Python course first.

There is no assumption that you know Git, PowerShell, Docker, MQTT, databases or what a virtual environment is. You will encounter some of those words elsewhere in the repository. You can safely ignore most of them for the first installation.

## The target result

When this is finished, your setup should look like this:

```text
Outdoor weather sensors
        |
        v
Original weather console
        |
        | home Wi-Fi
        v
Windows PC running MISOL Local
        |
        +--> local browser dashboard
        +--> SQLite weather history
        +--> JSON / CSV
```

The original console still works. MISOL Local simply becomes another destination for the readings.

## Before starting

Make sure:

1. the Windows PC is connected to your normal home network;
2. the weather console is connected, or can be connected, to the same home network;
3. the console is using its mains adaptor, not only backup batteries;
4. you have extracted the MISOL Local ZIP into a normal folder.

A folder such as this is fine:

```text
C:\Users\Matt\Documents\misol-local
```

A folder inside `Downloads` is also fine. Running directly from the ZIP is not.

---

# Part 1 — install Python

## Step 1

Open your web browser and go to the official Python website:

```text
https://www.python.org/downloads/windows/
```

Install Python **3.11 or newer**.

## Step 2

On the first Python installer screen, tick:

```text
Add python.exe to PATH
```

Then choose the normal installation.

That little checkbox saves an unreasonable quantity of future explanation.

## Step 3

When the Python installer finishes, close it.

You do not need to open Python itself.

---

# Part 2 — start MISOL Local

## Step 4

Open the extracted `misol-local` folder.

Find:

```text
START-HERE-WINDOWS.bat
```

Double-click it.

## Step 5

A black command window opens.

On the first run it creates a `.venv` folder and installs the project. Do not delete the window while it is working. Lines of package-installation text are normal.

When Windows Firewall asks about Python, tick **Private networks** and allow access.

Do not tick Public networks merely because the box exists.

## Step 6

Your browser should open this address:

```text
http://127.0.0.1:8080/
```

You should see **MISOL Local**.

It may say there are no readings yet. That is expected.

---

# Part 3 — prove the receiver works

Before changing the weather console, test the PC side.

## Step 7

Leave the MISOL Local black window running.

In the project folder, double-click:

```text
TEST-RECEIVER-WINDOWS.bat
```

A second window should report that a test packet was sent successfully.

## Step 8

Refresh the MISOL Local dashboard in your browser.

If a sample weather reading appears, the receiver and database are working.

If it does not appear, run:

```text
DIAGNOSE-WINDOWS.bat
```

Do not start changing router settings yet. First establish which half is actually broken.

---

# Part 4 — find the PC's address

The weather console needs the Windows PC's LAN address.

## Step 9

Double-click:

```text
GET-MY-IP-WINDOWS.bat
```

Look for an IPv4 address resembling:

```text
192.168.1.42
```

or:

```text
192.168.0.42
```

Write it down.

You may see more than one address if the PC has Ethernet, Wi-Fi, VPN software or virtual adapters. Usually the correct one belongs to the adapter that connects to your router.

### Important

Do **not** use:

```text
127.0.0.1
```

in the weather console.

`127.0.0.1` works in the browser on the PC because it means “this computer”. On the weather console it would mean “the weather console”, which is not where MISOL Local lives.

---

# Part 5 — configure the weather console

The exact screen varies by app and firmware, but you are looking for **Upload**, **Weather Services**, **Customised Website** or similar.

## Step 10

Enable the custom server/upload option.

Set:

```text
Protocol:      Ecowitt
Server:        YOUR_PC_IP
Path:          /data/report/
Port:          8080
Interval:      16 seconds
```

For example:

```text
Protocol:      Ecowitt
Server:        192.168.1.42
Path:          /data/report/
Port:          8080
Interval:      16 seconds
```

Save the settings.

If your app asks whether the server is HTTP or HTTPS, use ordinary **HTTP** for this local experimental receiver.

## Step 11

Wait 20 to 40 seconds.

Refresh:

```text
http://127.0.0.1:8080/
```

If the real weather data appears, the basic installation is finished.

---

# Part 6 — what to do next time

You do not need to run the setup again every day.

To start MISOL Local later, double-click:

```text
RUN-MISOL-LOCAL-WINDOWS.bat
```

To stop it, click the black window and press:

```text
Ctrl+C
```

Then close the window if it remains open.

---

# Part 7 — where the data is stored

Your database file is:

```text
data\misol.sqlite3
```

If you want a simple backup:

1. stop MISOL Local;
2. copy `data\misol.sqlite3` somewhere safe;
3. start MISOL Local again.

For spreadsheet use, open:

```text
http://127.0.0.1:8080/export.csv?limit=1000
```

Your browser will show or save CSV data depending on its settings.

---

# Part 8 — if the real weather station does not appear

Work through these in order.

## A. Does the fake test packet work?

Run:

```text
TEST-RECEIVER-WINDOWS.bat
```

If **no**, the problem is on the PC side. Run `DIAGNOSE-WINDOWS.bat`.

If **yes**, the PC side is broadly working. Continue below.

## B. Is the PC address correct?

Run:

```text
GET-MY-IP-WINDOWS.bat
```

Check the address in the console matches the PC's current LAN address.

Some routers change a PC's address after reboots. Once the project is working, reserving the PC's address in the router is sensible, but it is not required for the first test.

## C. Are both devices on the same network?

The PC and console should normally be on the same ordinary home LAN.

Guest Wi-Fi often isolates devices from one another. That is useful for guests and deeply unhelpful for a weather console trying to talk to a local server.

## D. Is the console using 2.4 GHz Wi-Fi?

Many EasyWeather/Fine Offset-derived consoles use 2.4 GHz Wi-Fi.

If your router uses one combined Wi-Fi name for 2.4 and 5 GHz, that may still work. If pairing fails, check that 2.4 GHz is enabled and not isolated.

## E. Is Windows Firewall blocking it?

The Python firewall rule should be allowed for **Private networks**.

As a test, open Windows Security > Firewall & network protection > Allow an app through firewall and confirm Python is permitted on the private network.

Do not leave the firewall disabled as a permanent “fix”. That solves one problem by inventing several less interesting ones.

## F. Is port 8080 already taken?

Run:

```text
DIAGNOSE-WINDOWS.bat
```

If another application already owns port 8080, edit `config.ini` and change:

```ini
port = 8080
```

to something else, for example:

```ini
port = 8090
```

Then restart MISOL Local and change the console upload port to the same number.

## G. Is the path correct?

Preferred Ecowitt path:

```text
/data/report/
```

MISOL Local accepts both the version with and without the final slash, but using the documented form avoids arguing with firmware that may care.

## H. Still nothing?

Start MISOL Local with debug logging:

```text
scripts\run_windows_debug.bat
```

Then trigger/save the console upload again.

If you report an issue, include:

- weather console model if known;
- firmware version if visible;
- whether the local fake packet works;
- the error text from the MISOL Local terminal;
- the upload protocol/path/port, with passwords and keys removed.

Do not post real PASSKEYs, passwords or cloud credentials.

---

# Part 9 — optional MQTT

Ignore this entire section until ordinary receiving works.

If you already have an MQTT broker, edit `config.ini`:

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

Restart MISOL Local.

Each observation is published to:

```text
misol-local/<station-id>/state
```

If you do not know what an MQTT broker is, leave `enabled = no`. Nothing is missing from the basic local logger.

---

# Part 10 — uninstalling it

MISOL Local does not install a Windows service or scatter files around the operating system.

To remove it:

1. stop the receiver;
2. copy `data\misol.sqlite3` somewhere else if you want the history;
3. delete the `misol-local` project folder.

That is it.

The Python installation can remain because other Python programs may use it. Remove Python separately through Windows **Installed apps** only if you know you no longer need it.
