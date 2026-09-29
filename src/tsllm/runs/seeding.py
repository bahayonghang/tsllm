"""Global random seeds for third-party libraries."""

import random
from importlib.util import find_spec

import numpy as np


def seed_everything(seed: int) -> None:
    # tsllm code passes explicit generators. Model libraries read the global generators.
    random.seed(seed)
    np.random.seed(seed)
    if find_spec("torch") is not None:
        import torch

        torch.manual_seed(seed)
