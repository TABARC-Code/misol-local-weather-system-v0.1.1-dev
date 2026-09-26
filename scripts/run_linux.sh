#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
python3 -m misol_local --config config.ini
