"""M3 stub adapter. Returns a valid arbitration-shaped payload."""

from __future__ import annotations

from typing import Any


def predict(inputs: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    _ = inputs, params
    return {"resolution": "escalate_human", "confidence": 0.0}
