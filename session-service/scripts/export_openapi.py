"""Export OpenAPI document for client type generation."""

from __future__ import annotations

import json
from pathlib import Path

from app.main import app


def main() -> None:
    spec = app.openapi()
    # FastAPI does not include WebSocket routes in OpenAPI; document the contract.
    spec.setdefault("paths", {})
    spec["paths"]["/v1/sessions/{session_id}/stream"] = {
        "get": {
            "summary": "Subscribe to session event stream (WebSocket)",
            "description": (
                "WebSocket endpoint. Upgrade from HTTP GET. "
                "Server pushes SessionEvent JSON objects after each append. "
                "Not a plain HTTP GET despite OpenAPI listing."
            ),
            "operationId": "stream_session_events",
            "parameters": [
                {
                    "name": "session_id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                }
            ],
            "responses": {
                "101": {"description": "Switching Protocols (WebSocket)"},
                "404": {"description": "session not found"},
            },
        }
    }
    out = Path(__file__).resolve().parents[1] / "openapi.json"
    out.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
