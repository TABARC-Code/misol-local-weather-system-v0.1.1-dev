"""Send one harmless local test report to MISOL Local.

EXPERIMENTAL helper for the Windows beginner setup.

This uses only Python's standard library. The PASSKEY value is deliberately fake
and exists only to exercise the same station-fingerprinting path as a real Ecowitt
upload. Do not replace it with a real credential merely for testing.
"""

from __future__ import annotations

import argparse
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a test weather report to MISOL Local")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    payload = {
        "PASSKEY": "MISOL-LOCAL-TEST-ONLY",
        "stationtype": "MISOL-Local-Test",
        "dateutc": "now",
        "tempf": "53.6",
        "humidity": "78",
        "tempinf": "68.0",
        "humidityin": "52",
        "baromrelin": "29.92",
        "baromabsin": "29.58",
        "winddir": "225",
        "windspeedmph": "4.5",
        "windgustmph": "8.3",
        "rainratein": "0.01",
        "dailyrainin": "0.04",
        "solarradiation": "123.4",
        "uv": "1",
    }

    body = urlencode(payload).encode("ascii")
    url = f"http://{args.host}:{args.port}/data/report/"
    request = Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    print(f"Sending test observation to {url}")
    try:
        with urlopen(request, timeout=5) as response:
            print(f"Receiver replied with HTTP {response.status}.")
    except HTTPError as exc:
        print(f"Receiver returned HTTP {exc.code}: {exc.reason}")
        return 2
    except URLError as exc:
        print("Could not reach MISOL Local.")
        print(f"Reason: {exc.reason}")
        print("Make sure RUN-MISOL-LOCAL-WINDOWS.bat is already running.")
        return 3

    print(f"Test packet sent. Refresh http://{args.host}:{args.port}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
