"""Self-check for the MAST judge response parser."""

from __future__ import annotations

from pathlib import Path

from models.baseline_mast.parse_judge import (
    PARSER_VERSION,
    parse_judge_response,
)

FIXTURE = (
    Path(__file__).parent
    / "tests"
    / "fixtures"
    / "all_yes_template.txt"
)


def main() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    parsed = parse_judge_response(text)
    assert parsed.parse_status == "ok"
    assert len(parsed.predicted_labels) == 14
    assert sum(parsed.labels_official.values()) == 12
    print("mast parser ok", PARSER_VERSION)


if __name__ == "__main__":
    main()
