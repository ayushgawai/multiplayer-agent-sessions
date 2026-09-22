"""M4 stub adapter. Returns a valid routing-shaped payload."""

from __future__ import annotations

from typing import Any


def predict(inputs: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    _ = inputs, params
    return {
        "dag": {"nodes": ["goal"], "edges": []},
        "assignment": [],
        "valid": True,
    }
