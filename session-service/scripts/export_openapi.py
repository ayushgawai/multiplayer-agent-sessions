"""Export OpenAPI document for client type generation."""

from __future__ import annotations

import json
from pathlib import Path

from app.main import app


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "openapi.json"
    out.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
