"""Self-check for checkpoint save/resume."""

from __future__ import annotations

import shutil
from pathlib import Path

from models.common.checkpointing import resume_from_checkpoint, save_checkpoint


def main() -> None:
    root = Path("/tmp/mas_ckpt_demo")
    if root.exists():
        shutil.rmtree(root)
    src = root / "src"
    uri = f"file://{(root / 'remote').resolve()}"
    src.mkdir(parents=True, exist_ok=True)
    (src / "adapter.bin").write_bytes(b"demo")
    save_checkpoint(src, uri, step=200, meta={"candidate_id": "m1-a"})
    save_checkpoint(src, uri, step=400, meta={"candidate_id": "m1-a"})
    latest = resume_from_checkpoint(uri)
    assert latest is not None and latest.name == "step-400"
    print("checkpointing ok", latest)
    shutil.rmtree(root)

    try:
        import fsspec  # noqa: F401
    except ImportError:
        print("fsspec not installed; skipping memory:// round-trip")
        return
    uri = "memory://mas_ckpt_demo"
    src.mkdir(parents=True, exist_ok=True)
    (src / "adapter.bin").write_bytes(b"demo")
    save_checkpoint(src, uri, step=200)
    save_checkpoint(src, uri, step=400, meta={"candidate_id": "m1-a"})
    latest = resume_from_checkpoint(uri)
    assert latest is not None and latest.name == "step-400", latest
    assert (latest / "adapter.bin").read_bytes() == b"demo"
    assert "m1-a" in (latest / "checkpoint_meta.json").read_text()
    print("remote checkpointing ok", latest)
    shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
