"""M2 stub adapter. Returns a valid attribution-shaped payload."""

from __future__ import annotations

from typing import Any


def predict(inputs: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    _ = params
    roster = inputs.get("roster") or ["shared"]
    return {"gold_actor": roster[0], "confidence": 0.0}
