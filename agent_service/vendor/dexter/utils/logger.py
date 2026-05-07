"""Stdlib logging wrapper used across the package."""

from __future__ import annotations

import logging
import os
import sys

_logger: logging.Logger | None = None


def get_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger
    lg = logging.getLogger("dexter")
    if not lg.handlers:
        h = logging.StreamHandler(sys.stderr)
        h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        lg.addHandler(h)
    lg.setLevel(os.environ.get("DEXTER_LOG_LEVEL", "WARNING").upper())
    _logger = lg
    return lg


logger = get_logger()
