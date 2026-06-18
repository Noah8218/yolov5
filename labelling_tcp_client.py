#!/usr/bin/env python3
"""Compatibility entry point for the old British spelling file name."""

from __future__ import annotations

import sys

from labeling_tcp_client import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
