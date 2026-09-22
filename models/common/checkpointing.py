"""Shared checkpoint save/resume for all training scripts.

Base weights are re-downloaded from Hugging Face each run. Only adapters or
encoder weights under ~500 MB are pushed to remote storage every save_steps.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _local_path(uri: str) -> Path:
    parsed = urlparse(uri)
    if parsed.scheme in ("", "file"):
        path = parsed.path if parsed.scheme == "file" else uri
        return Path(path)
    raise ValueError(
        f"unsupported checkpoint URI scheme {parsed.scheme!r}; "
        "use file:// for local runs or extend this helper for remote storage"
    )


def save_checkpoint(
    local_dir: str | Path,
    checkpoint_uri: str,
    step: int,
    meta: dict[str, Any] | None = None,
) -> Path:
    """Copy a local trainer output directory to checkpoint_uri/step-{step}/."""
    src = Path(local_dir)
    if not src.exists():
        raise FileNotFoundError(src)
    dest_root = _local_path(checkpoint_uri)
    dest = dest_root / f"step-{step}"
    dest.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dest / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
    payload = {"step": step, **(meta or {})}
    (dest / "checkpoint_meta.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    return dest


def resume_from_checkpoint(checkpoint_uri: str) -> Path | None:
    """Return the newest step-* directory under checkpoint_uri, if any."""
    root = _local_path(checkpoint_uri)
    if not root.exists():
        return None
    steps = sorted(root.glob("step-*"), key=lambda p: int(p.name.split("-")[1]))
    return steps[-1] if steps else None
