"""Shared checkpoint save/resume for all training scripts.

Base weights are re-downloaded from Hugging Face each run. Only adapters or
encoder weights under ~500 MB are pushed to remote storage every save_steps.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _local_path(uri: str) -> Path | None:
    """Local Path for file:// or bare paths; None for remote URIs (s3://, memory://, ...)."""
    parsed = urlparse(uri)
    if parsed.scheme in ("", "file"):
        path = parsed.path if parsed.scheme == "file" else uri
        return Path(path)
    return None


def _fs(uri: str) -> Any:
    import fsspec  # lazy: only needed for remote URIs

    return fsspec.core.url_to_fs(uri)[0]


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
    payload = {"step": step, **(meta or {})}
    if dest_root is None:
        fs, remote = _fs(checkpoint_uri), f"{checkpoint_uri.rstrip('/')}/step-{step}"
        fs.put(str(src) + "/", remote + "/", recursive=True)
        with fs.open(f"{remote}/checkpoint_meta.json", "w") as f:
            f.write(json.dumps(payload, indent=2) + "\n")
        return remote  # type: ignore[return-value]  # remote URI string
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
    (dest / "checkpoint_meta.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    return dest


def resume_from_checkpoint(checkpoint_uri: str) -> Path | None:
    """Return the newest step-* directory under checkpoint_uri, if any."""
    root = _local_path(checkpoint_uri)
    if root is None:
        fs, base = _fs(checkpoint_uri), checkpoint_uri.rstrip("/")
        found = fs.ls(base, detail=False) if fs.exists(base) else []
        names = [p.rstrip("/").rsplit("/", 1)[-1] for p in found]
        names = sorted((n for n in names if n.startswith("step-")), key=lambda n: int(n.split("-")[1]))
        if not names:
            return None
        cache = Path(tempfile.mkdtemp(prefix="mas_ckpt_")) / names[-1]
        fs.get(f"{base}/{names[-1]}/", str(cache) + "/", recursive=True)
        return cache
    if not root.exists():
        return None
    steps = sorted(root.glob("step-*"), key=lambda p: int(p.name.split("-")[1]))
    return steps[-1] if steps else None
