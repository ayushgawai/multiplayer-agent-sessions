"""The memory failure vocabulary must stay equal to the evaluators' own.

A lesson records the same failure a candidate's evaluator reports, so the two
vocabularies have to be one vocabulary. This compares what `memory/schema.py`
accepts against the `failure_codes` of every candidate config that exists, so
a change on either side that is not mirrored on the other fails the build.
A task whose configs have not landed yet is skipped rather than guessed at.

Linear: DAT-56 (M1-05). Owner: Shriram Dundigalla.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from memory.schema import MAST_FAILURE_CODES, Task, _TASK_FAILURE_CODES, failure_codes_for

CONFIG_DIR = Path(__file__).resolve().parents[2] / "eval" / "configs"


def candidate_configs(task: Task) -> list[Path]:
    """The per-candidate configs for a task, not the task's contract file."""
    return sorted(CONFIG_DIR.glob(f"{task.value}-?.yaml"))


@pytest.mark.parametrize("task", list(Task))
def test_memory_mirrors_the_candidate_failure_codes(task: Task) -> None:
    configs = candidate_configs(task)
    if not configs:
        pytest.skip(f"{task.value} has no candidate configs yet")

    expected = set(_TASK_FAILURE_CODES[task])
    for config in configs:
        declared = set(yaml.safe_load(config.read_text(encoding="utf-8"))["failure_codes"])
        assert declared == expected, (
            f"{config.name} declares {sorted(declared)} but memory accepts "
            f"{sorted(expected)} for {task.value}"
        )


def test_at_least_one_task_is_actually_checked() -> None:
    """Guards against the skip above quietly covering every task."""
    assert any(candidate_configs(task) for task in Task)


def test_mast_codes_are_namespaced_so_they_cannot_collide_with_task_codes() -> None:
    task_codes = {code for codes in _TASK_FAILURE_CODES.values() for code in codes}

    assert all(code.startswith("mast.") for code in MAST_FAILURE_CODES)
    assert not task_codes & set(MAST_FAILURE_CODES)


@pytest.mark.parametrize("task", list(Task))
def test_every_task_accepts_its_own_codes_plus_mast(task: Task) -> None:
    accepted = failure_codes_for(task)

    assert set(accepted) == set(_TASK_FAILURE_CODES[task]) | set(MAST_FAILURE_CODES)
