"""Unit tests for data/scripts/download_mast.py (MAST 04 / DAT-28).

Owner: Naman Chheda. No network calls: huggingface_hub.hf_hub_download and
requests.get are monkeypatched wherever a test would otherwise reach the network.

Run with: pytest data/tests/test_download_mast.py -q
(or `cd data && pytest -q`, matching the per-package convention used by
session-service/tests and serving/tests.)
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

# download_mast.py is a standalone script, not part of an importable package;
# add its directory to sys.path the same way `python data/scripts/download_mast.py`
# would find it, then import it as a plain module.
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import download_mast as dm  # noqa: E402


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path, monkeypatch):
    """Point every module-level path constant at a throwaway directory.

    Every test in this file that touches the filesystem uses this tmp layout
    instead of the real data/mast/, so nothing here can write into or depend on
    an actual download.
    """
    data_dir = tmp_path / "mast"
    hf_dir = data_dir / "hf"
    taxonomy_dir = data_dir / "taxonomy"
    monkeypatch.setattr(dm, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(dm, "DATA_DIR", data_dir)
    monkeypatch.setattr(dm, "HF_DIR", hf_dir)
    monkeypatch.setattr(dm, "TAXONOMY_DIR", taxonomy_dir)
    monkeypatch.setattr(dm, "STATS_PATH", data_dir / "STATS.md")
    return data_dir


def _new_stats() -> dm.RunStats:
    return dm.RunStats(started_at="2026-01-01T00:00:00+00:00")


# ---------------------------------------------------------------------------
# Record counting logic
# ---------------------------------------------------------------------------


def test_count_records_list_payload():
    assert dm.count_records([1, 2, 3]) == 3


def test_count_records_empty_list():
    assert dm.count_records([]) == 0


def test_count_records_dict_with_list_value():
    assert dm.count_records({"data": [1, 2], "meta": "x"}) == 2


def test_count_records_dict_prefers_first_list_value_in_order():
    # dict preserves insertion order; the first list-valued entry wins.
    payload = {"meta": "x", "train": [1, 2, 3], "other_list": [1]}
    assert dm.count_records(payload) == 3


def test_count_records_dict_with_no_list_value_is_none():
    assert dm.count_records({"meta": "x", "count": 5}) is None


@pytest.mark.parametrize("payload", [42, "a string", None, 3.14, True])
def test_count_records_malformed_scalar_payload_is_none(payload):
    assert dm.count_records(payload) is None


def test_count_records_nested_list_is_not_flattened():
    # A list of lists still just counts the outer list, matching the real
    # MAD_full_dataset.json shape (a flat list of record dicts).
    assert dm.count_records([[1, 2], [3, 4], [5, 6]]) == 3


# ---------------------------------------------------------------------------
# Revision pinning
# ---------------------------------------------------------------------------


def test_hf_revision_is_the_pinned_commit_sha():
    assert dm.HF_REVISION == "95118ac951421753cf1deb87ddea3b01e693c41b"


def test_no_latest_revision_resolution_helper_exists_for_hf():
    # The old dataset_info()-based "resolve latest sha" path is gone entirely:
    # no HfApi import, and the only resolver left is for the GitHub taxonomy
    # files, not the HF release.
    assert not hasattr(dm, "HfApi")
    assert not hasattr(dm, "dataset_info")


def test_hf_filenames_are_exactly_the_three_pinned_files():
    assert dm.HF_FILENAMES == (
        "MAD_full_dataset.json",
        "MAD_human_labelled_dataset.json",
        "README.md",
    )


def test_taxonomy_revision_and_checksums_are_pinned():
    assert dm.MAST_GITHUB_REVISION == "a70542e541b2104ef8fcd785778179e173fb8d70"
    assert set(dm.EXPECTED_TAXONOMY_CHECKSUMS) == set(dm.GITHUB_TAXONOMY_FILES)
    assert all(len(checksum) == 64 for checksum in dm.EXPECTED_TAXONOMY_CHECKSUMS.values())


def test_no_latest_revision_resolution_helper_exists_for_taxonomy():
    assert not hasattr(dm, "resolve_github_main_sha")
    assert not hasattr(dm, "MAST_GITHUB_API_COMMITS_URL")


def test_download_hf_release_always_requests_the_pinned_revision(monkeypatch):
    seen_revisions = []

    def fake_hf_hub_download(*, repo_id, repo_type, filename, revision, local_dir, force_download):
        seen_revisions.append(revision)
        dest = Path(local_dir) / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        content = f"content for {filename}".encode()
        dest.write_bytes(content)
        # Make the checksum line up so this test only exercises revision plumbing.
        monkeypatch.setitem(dm.EXPECTED_HF_CHECKSUMS, filename, _sha256(content))
        return str(dest)

    monkeypatch.setattr(dm, "hf_hub_download", fake_hf_hub_download)

    stats = _new_stats()
    dm.download_hf_release(force=False, stats=stats)

    assert seen_revisions == [dm.HF_REVISION] * len(dm.HF_FILENAMES)
    assert stats.hf_revision == dm.HF_REVISION
    assert all(dm.HF_REVISION in rec.source_url for rec in stats.files)


def test_download_taxonomy_uses_pinned_revision_and_validates_checksums(monkeypatch):
    requested_urls = []
    content_by_path = {rel: f"content for {rel}".encode() for rel in dm.GITHUB_TAXONOMY_FILES}
    for rel, content in content_by_path.items():
        monkeypatch.setitem(dm.EXPECTED_TAXONOMY_CHECKSUMS, rel, _sha256(content))

    class FakeResponse:
        def __init__(self, content):
            self.content = content

        def raise_for_status(self):
            return None

    def fake_get(url, timeout):
        requested_urls.append(url)
        rel = next(rel for rel in dm.GITHUB_TAXONOMY_FILES if url.endswith(rel))
        return FakeResponse(content_by_path[rel])

    monkeypatch.setattr(dm.requests, "get", fake_get)

    stats = _new_stats()
    dm.download_github_taxonomy(force=False, stats=stats)

    assert stats.github_taxonomy_sha == dm.MAST_GITHUB_REVISION
    assert len(requested_urls) == len(dm.GITHUB_TAXONOMY_FILES)
    assert all(dm.MAST_GITHUB_REVISION in url for url in requested_urls)
    assert all(rec.status == "downloaded (verified against pinned sha)" for rec in stats.files)


def test_download_taxonomy_fails_on_checksum_mismatch(monkeypatch):
    class FakeResponse:
        content = b"unexpected taxonomy bytes"

        def raise_for_status(self):
            return None

    monkeypatch.setattr(dm.requests, "get", lambda url, timeout: FakeResponse())

    with pytest.raises(dm.ChecksumMismatchError, match="pinned MAST taxonomy revision"):
        dm.download_github_taxonomy(force=False, stats=_new_stats())


# ---------------------------------------------------------------------------
# Checksum mismatch handling
# ---------------------------------------------------------------------------


def test_verify_checksum_passes_when_matching():
    filename = "MAD_full_dataset.json"
    expected = dm.EXPECTED_HF_CHECKSUMS[filename]
    dm.verify_checksum(filename, expected)  # must not raise


def test_verify_checksum_raises_on_mismatch():
    filename = "MAD_full_dataset.json"
    with pytest.raises(dm.ChecksumMismatchError, match=filename):
        dm.verify_checksum(filename, "0" * 64)


def test_verify_checksum_is_a_noop_for_unpinned_filenames():
    # A filename with no pinned expectation should not raise (defensive: should
    # never happen for the 3 pinned files, but must not crash if it does).
    dm.verify_checksum("some_other_file.json", "0" * 64)


def test_download_hf_release_raises_when_downloaded_file_checksum_is_wrong(monkeypatch):
    def fake_hf_hub_download(*, repo_id, repo_type, filename, revision, local_dir, force_download):
        dest = Path(local_dir) / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"not the expected bytes at all")
        return str(dest)

    monkeypatch.setattr(dm, "hf_hub_download", fake_hf_hub_download)

    stats = _new_stats()
    with pytest.raises(dm.ChecksumMismatchError):
        dm.download_hf_release(force=False, stats=stats)


# ---------------------------------------------------------------------------
# Cached-file behavior
# ---------------------------------------------------------------------------


def test_cached_file_is_not_redownloaded_but_is_checksum_validated(monkeypatch):
    filename = "MAD_full_dataset.json"
    content = b'{"records": [1, 2, 3]}'
    dm.HF_DIR.mkdir(parents=True, exist_ok=True)
    (dm.HF_DIR / filename).write_bytes(content)
    monkeypatch.setitem(dm.EXPECTED_HF_CHECKSUMS, filename, _sha256(content))
    for other in dm.HF_FILENAMES:
        if other != filename:
            monkeypatch.setitem(dm.EXPECTED_HF_CHECKSUMS, other, _sha256(f"cached {other}".encode()))
            (dm.HF_DIR / other).write_bytes(f"cached {other}".encode())

    def fail_if_called(**kwargs):
        raise AssertionError(
            f"hf_hub_download should not be called for a cached file (got {kwargs!r})"
        )

    monkeypatch.setattr(dm, "hf_hub_download", fail_if_called)

    stats = _new_stats()
    dm.download_hf_release(force=False, stats=stats)  # must not raise, must not download

    rec = next(r for r in stats.files if r.relative_path.endswith(filename))
    assert rec.status == "skipped (cached)"
    assert rec.sha256 == _sha256(content)


def test_cached_file_with_wrong_checksum_still_fails_loudly(monkeypatch):
    filename = "MAD_full_dataset.json"
    dm.HF_DIR.mkdir(parents=True, exist_ok=True)
    # Pinned expected checksum is the real one; the file on disk is stale/corrupt.
    (dm.HF_DIR / filename).write_bytes(b"stale bytes from before the revision was pinned")
    for other in dm.HF_FILENAMES:
        if other != filename:
            content = f"cached {other}".encode()
            monkeypatch.setitem(dm.EXPECTED_HF_CHECKSUMS, other, _sha256(content))
            (dm.HF_DIR / other).write_bytes(content)

    def fail_if_called(**kwargs):
        raise AssertionError("cached path must not re-download; it must fail on checksum instead")

    monkeypatch.setattr(dm, "hf_hub_download", fail_if_called)

    stats = _new_stats()
    with pytest.raises(dm.ChecksumMismatchError, match=filename):
        dm.download_hf_release(force=False, stats=stats)


def test_force_redownloads_even_when_cached(monkeypatch):
    filename = "MAD_full_dataset.json"
    dm.HF_DIR.mkdir(parents=True, exist_ok=True)
    (dm.HF_DIR / filename).write_bytes(b"old cached bytes")
    calls = []

    def fake_hf_hub_download(*, repo_id, repo_type, filename, revision, local_dir, force_download):
        calls.append(filename)
        dest = Path(local_dir) / filename
        content = f"fresh content for {filename}".encode()
        dest.write_bytes(content)
        monkeypatch.setitem(dm.EXPECTED_HF_CHECKSUMS, filename, _sha256(content))
        return str(dest)

    monkeypatch.setattr(dm, "hf_hub_download", fake_hf_hub_download)

    stats = _new_stats()
    dm.download_hf_release(force=True, stats=stats)

    assert calls == list(dm.HF_FILENAMES)
    assert all(rec.status == "downloaded" for rec in stats.files)


# ---------------------------------------------------------------------------
# Record count validation (fails loudly, does not just warn)
# ---------------------------------------------------------------------------


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_inspect_dataset_passes_when_counts_match():
    dm.HF_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(dm.HF_DIR / dm.FULL_DATASET_FILENAME, list(range(dm.EXPECTED_TRACE_COUNT)))
    _write_json(dm.HF_DIR / dm.HUMAN_LABELLED_FILENAME, list(range(dm.EXPECTED_HUMAN_LABELLED_COUNT)))

    stats = _new_stats()
    dm.inspect_dataset(stats=stats)

    assert stats.record_count == dm.EXPECTED_TRACE_COUNT
    assert stats.human_labelled_count == dm.EXPECTED_HUMAN_LABELLED_COUNT
    assert "MATCH" in stats.record_count_note


def test_inspect_dataset_raises_on_full_dataset_count_mismatch():
    dm.HF_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(dm.HF_DIR / dm.FULL_DATASET_FILENAME, list(range(dm.EXPECTED_TRACE_COUNT - 1)))
    _write_json(dm.HF_DIR / dm.HUMAN_LABELLED_FILENAME, list(range(dm.EXPECTED_HUMAN_LABELLED_COUNT)))

    stats = _new_stats()
    with pytest.raises(dm.RecordCountMismatchError, match=dm.FULL_DATASET_FILENAME):
        dm.inspect_dataset(stats=stats)


def test_inspect_dataset_raises_on_human_labelled_count_mismatch():
    dm.HF_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(dm.HF_DIR / dm.FULL_DATASET_FILENAME, list(range(dm.EXPECTED_TRACE_COUNT)))
    _write_json(dm.HF_DIR / dm.HUMAN_LABELLED_FILENAME, list(range(dm.EXPECTED_HUMAN_LABELLED_COUNT + 5)))

    stats = _new_stats()
    with pytest.raises(dm.RecordCountMismatchError, match=dm.HUMAN_LABELLED_FILENAME):
        dm.inspect_dataset(stats=stats)


def test_inspect_dataset_raises_on_missing_full_dataset_file():
    dm.HF_DIR.mkdir(parents=True, exist_ok=True)
    # MAD_full_dataset.json intentionally absent.
    stats = _new_stats()
    with pytest.raises(FileNotFoundError, match=dm.FULL_DATASET_FILENAME):
        dm.inspect_dataset(stats=stats)


def test_inspect_dataset_raises_on_missing_human_labelled_file():
    dm.HF_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(dm.HF_DIR / dm.FULL_DATASET_FILENAME, list(range(dm.EXPECTED_TRACE_COUNT)))
    # MAD_human_labelled_dataset.json intentionally absent.
    stats = _new_stats()
    with pytest.raises(FileNotFoundError, match=dm.HUMAN_LABELLED_FILENAME):
        dm.inspect_dataset(stats=stats)


# ---------------------------------------------------------------------------
# Unexpected / malformed dataset structure
# ---------------------------------------------------------------------------


def test_inspect_dataset_raises_when_full_dataset_json_is_malformed():
    dm.HF_DIR.mkdir(parents=True, exist_ok=True)
    # Neither a list nor a dict containing a list -> count_records returns None,
    # which can never equal EXPECTED_TRACE_COUNT, so this must fail loudly too.
    _write_json(dm.HF_DIR / dm.FULL_DATASET_FILENAME, {"schema_version": 2, "note": "not a list"})
    _write_json(dm.HF_DIR / dm.HUMAN_LABELLED_FILENAME, list(range(dm.EXPECTED_HUMAN_LABELLED_COUNT)))

    stats = _new_stats()
    with pytest.raises(dm.RecordCountMismatchError, match=dm.FULL_DATASET_FILENAME):
        dm.inspect_dataset(stats=stats)
    assert stats.record_count is None


def test_inspect_dataset_raises_when_full_dataset_json_is_a_bare_scalar():
    dm.HF_DIR.mkdir(parents=True, exist_ok=True)
    (dm.HF_DIR / dm.FULL_DATASET_FILENAME).write_text("42", encoding="utf-8")
    _write_json(dm.HF_DIR / dm.HUMAN_LABELLED_FILENAME, list(range(dm.EXPECTED_HUMAN_LABELLED_COUNT)))

    stats = _new_stats()
    with pytest.raises(dm.RecordCountMismatchError):
        dm.inspect_dataset(stats=stats)


def test_inspect_dataset_raises_on_invalid_json_syntax():
    dm.HF_DIR.mkdir(parents=True, exist_ok=True)
    (dm.HF_DIR / dm.FULL_DATASET_FILENAME).write_text("{not valid json", encoding="utf-8")

    stats = _new_stats()
    with pytest.raises(json.JSONDecodeError):
        dm.inspect_dataset(stats=stats)


# ---------------------------------------------------------------------------
# main(): fails loudly / non-zero exit, does not just warn
# ---------------------------------------------------------------------------


def test_main_returns_nonzero_and_does_not_write_stats_on_checksum_failure(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["download_mast.py"])
    monkeypatch.setattr(
        dm,
        "download_hf_release",
        lambda force, stats: (_ for _ in ()).throw(dm.ChecksumMismatchError("boom")),
    )

    exit_code = dm.main()

    assert exit_code == 1
    assert not dm.STATS_PATH.exists()


def test_main_returns_nonzero_on_record_count_mismatch(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["download_mast.py"])
    monkeypatch.setattr(dm, "download_hf_release", lambda force, stats: None)
    monkeypatch.setattr(dm, "download_github_taxonomy", lambda force, stats: None)
    monkeypatch.setattr(
        dm,
        "inspect_dataset",
        lambda stats: (_ for _ in ()).throw(dm.RecordCountMismatchError("boom")),
    )

    exit_code = dm.main()

    assert exit_code == 1
    assert not dm.STATS_PATH.exists()


def test_main_writes_stats_and_returns_zero_on_success(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["download_mast.py"])

    def fake_download_hf_release(force, stats):
        stats.hf_revision = dm.HF_REVISION

    def fake_download_github_taxonomy(force, stats):
        stats.github_taxonomy_sha = "deadbeef"

    def fake_inspect_dataset(stats):
        stats.record_count = dm.EXPECTED_TRACE_COUNT
        stats.record_count_note = "MATCH: fake"
        stats.human_labelled_count = dm.EXPECTED_HUMAN_LABELLED_COUNT

    monkeypatch.setattr(dm, "download_hf_release", fake_download_hf_release)
    monkeypatch.setattr(dm, "download_github_taxonomy", fake_download_github_taxonomy)
    monkeypatch.setattr(dm, "inspect_dataset", fake_inspect_dataset)

    exit_code = dm.main()

    assert exit_code == 0
    assert dm.STATS_PATH.exists()
    text = dm.STATS_PATH.read_text(encoding="utf-8")
    assert dm.HF_REVISION in text
    assert "MATCH: fake" in text
