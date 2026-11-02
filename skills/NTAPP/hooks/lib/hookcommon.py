"""Shared helpers for NTAPP Python hooks."""
from __future__ import annotations

import os

_TRUTHY = {"1", "true", "yes", "on"}


def is_true(val: str | None) -> bool:
    return (val or "").strip().lower() in _TRUTHY


def hook_disabled(name: str) -> bool:
    """True nếu hook bị tắt qua env.

    DISABLE_HOOKS_ALL=1 tắt mọi hook; DISABLE_HOOK_<NAME>=1 tắt riêng,
    NAME = tên hook viết HOA (vd 'drift_detector' → DISABLE_HOOK_DRIFT_DETECTOR).
    """
    if is_true(os.environ.get("DISABLE_HOOKS_ALL")):
        return True
    var = "DISABLE_HOOK_" + name.upper().replace("-", "_")
    return is_true(os.environ.get(var))
