"""Build the MAST judge prompt byte-identical to upstream commit a70542e.

The committed template in judge_prompt.txt is frozen as mast-judge-v1.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

PROMPT_VERSION: str = "mast-judge-v1"
UPSTREAM_REPO: str = (
    "https://github.com/multi-agent-systems-failure-taxonomy/MAST"
)
UPSTREAM_COMMIT: str = "a70542e541b2104ef8fcd785778179e173fb8d70"
PROMPT_FILE: Path = Path(__file__).parent / "judge_prompt.txt"
PROMPT_SHA256: str = (
    "6a73fd53d0e559cd0ee131adec530cf11f687f008132ae8c29a3eedff81bca7c"
)
TRACE_TOKEN: str = "<<TRACE>>"
UPSTREAM_MAX_CHARS: int = 1048570
UPSTREAM_EXAMPLES_CHARS: int = 67469
MAX_TRACE_CHARS: int = UPSTREAM_MAX_CHARS - UPSTREAM_EXAMPLES_CHARS
# Reference condition from upstream only. The environment owner's adapter
# decides the actual model and records it on each prediction.
JUDGE_MODEL: str = "o1"
JUDGE_TEMPERATURE: float = 1.0


def load_template() -> str:
    """Load and integrity-check the frozen judge_prompt.txt template."""
    with open(PROMPT_FILE, encoding="utf-8", newline="") as f:
        text = f.read()
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if digest != PROMPT_SHA256:
        raise ValueError(
            f"judge_prompt.txt sha256 {digest} != expected {PROMPT_SHA256}"
        )
    count = text.count(TRACE_TOKEN)
    if count != 1:
        raise ValueError(
            f"TRACE_TOKEN {TRACE_TOKEN!r} occurs {count} times; expected 1"
        )
    return text


def truncate_trace(trace: str) -> str:
    """Apply the upstream length rule before embedding the trace."""
    if len(trace) > MAX_TRACE_CHARS:
        return trace[:MAX_TRACE_CHARS]
    return trace


def render_prompt(trace: str) -> str:
    """Substitute the truncated trace into the frozen template once."""
    before, after = load_template().split(TRACE_TOKEN, 1)
    return before + truncate_trace(trace) + after


def build_messages(trace: str) -> list[dict[str, str]]:
    """Return the single-user-message payload matching upstream o1 calls."""
    return [{"role": "user", "content": render_prompt(trace)}]


def was_truncated(trace: str) -> bool:
    """True when truncate_trace would shorten the input."""
    return len(trace) > MAX_TRACE_CHARS


def prompt_metadata() -> dict[str, str | int | float]:
    """Fields the execution owner copies into every prediction record."""
    return {
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": PROMPT_SHA256,
        "upstream_commit": UPSTREAM_COMMIT,
        "max_trace_chars": MAX_TRACE_CHARS,
        "reference_model": JUDGE_MODEL,
        "reference_temperature": JUDGE_TEMPERATURE,
    }
