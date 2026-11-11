"""One deterministic seeding entry point for every evaluation run."""

from __future__ import annotations

import os
import random
from collections.abc import Callable

import numpy as np


def set_all_seeds(seed: int) -> Callable[[int], None]:
    """Seed Python, NumPy, and PyTorch when installed.

    Returns a dataloader worker initializer that derives a stable worker seed.
    """

    if seed < 0:
        raise ValueError("seed must be non-negative")
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)

    try:
        import torch  # type: ignore[import-not-found]
    except ImportError:
        torch = None  # type: ignore[assignment]

    if torch is not None:
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        if hasattr(torch.backends, "cudnn"):
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
        try:
            torch.use_deterministic_algorithms(True, warn_only=True)
        except AttributeError:
            pass

    def worker_init_fn(worker_id: int) -> None:
        worker_seed = (seed + worker_id) % (2**32)
        random.seed(worker_seed)
        np.random.seed(worker_seed)

    return worker_init_fn
