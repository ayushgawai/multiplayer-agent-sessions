"""Self-check for the frozen MAST judge prompt template."""

from __future__ import annotations

import hashlib

from models.baseline_mast.prompt import (
    PROMPT_SHA256,
    PROMPT_VERSION,
    build_messages,
    load_template,
    render_prompt,
)


def main() -> None:
    load_template()
    rendered = render_prompt("<<TRACE>>")
    digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    assert len(rendered) == 83204
    assert digest == PROMPT_SHA256
    messages = build_messages("<<TRACE>>")
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    print("mast prompt ok", PROMPT_VERSION, PROMPT_SHA256[:12])


if __name__ == "__main__":
    main()
