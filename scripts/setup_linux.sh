#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."

printf '%s\n' 'MISOL Local - EXPERIMENTAL Linux setup'

PYTHON="${PYTHON:-python3}"
"$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' || {
    echo 'Python 3.11 or newer is required.' >&2
    exit 2
}

if [ ! -x .venv/bin/python ]; then
    "$PYTHON" -m venv .venv
fi

. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
python -m pip install -r requirements-optional.txt || echo 'WARNING: optional MQTT support did not install.'

[ -f config.ini ] || cp config.example.ini config.ini
mkdir -p data
python -m unittest discover -s tests -v

echo
echo 'Setup complete. Run ./scripts/run_linux.sh'
