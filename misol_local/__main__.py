"""Command line entry point for MISOL Local."""

from __future__ import annotations

import argparse
import logging

from . import __version__
from .config import load_config
from .server import run_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="misol-local",
        description="EXPERIMENTAL local receiver for MISOL/Fine Offset-style weather uploads",
    )
    parser.add_argument("--config", default="config.ini", help="INI configuration path")
    parser.add_argument("--host", help="override listen address")
    parser.add_argument("--port", type=int, help="override listen port")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = load_config(args.config)
    if args.host:
        config.server.host = args.host
    if args.port:
        config.server.port = args.port
    run_server(config)


if __name__ == "__main__":
    main()
