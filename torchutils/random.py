# -*- coding: utf-8 -*-

from typing import Optional
import torch
import random
import numpy as np

from torchutils.types import RandState

_META_RNG = None
_SEED = None
_SEED_RANGE = 0

_DEFAULT_META_SEED = 9223372036854775783  # The God Number (closest to 2^63-1)
_DEFAULT_META_RAND_RANGE = 170141183460469231731687303715884105727  # 2^127 - 1
_NP_MAX_SEED_RANGE = 4294967287  # 2147483659 with _DEFAULT_META_SEED
_TORCH_MAX_SEED_RANGE = 4294967287  # 2147483659 with _DEFAULT_META_SEED

THE_SEED = None
NP_SEED = None
TORCH_SEED = None


def init_meta_rng(meta_seed: int = _DEFAULT_META_SEED, seed_range: int = _DEFAULT_META_RAND_RANGE, rand_state: Optional[RandState] = None):
    '''
    initialize meta rng
    '''
    global _META_RNG
    global _SEED_RANGE

    if _META_RNG is not None:
        return

    _META_RNG = random.Random(meta_seed)
    _SEED_RANGE = seed_range

    if rand_state is not None:
        set_meta_state(rand_state)


def reset_meta_rng():
    global _META_RNG
    _META_RNG = None


def monkeypatch_meta_rng(meta_seed: int = _DEFAULT_META_SEED, seed_range: int = _DEFAULT_META_RAND_RANGE, rand_state: Optional[RandState] = None):
    '''
    initialize meta rng and do monkeypatch.
    '''

    init_meta_rng(meta_seed=meta_seed, rand_state=rand_state, seed_range=seed_range)
    monkeypatch_seed()


def monkeypatch_seed():
    '''
    monkeypatch seed. Need to do init_meta_rng first if we want to have reproducible results.

    We use this function whenever we want to set a new seed (automatically generated from meta-random).
    '''
    if _META_RNG is None:
        return _monkeypatch_random(seed=None)

    seed = _get_seed(seed_range=_SEED_RANGE)
    _monkeypatch_random(seed=seed, cuda_deterministic=True)


def get_meta_state() -> RandState:
    '''
    Get meta random state
    '''
    return _META_RNG.getstate()


def set_meta_state(rand_state: RandState):
    '''
    Set meta random state
    '''
    global _META_RNG
    _META_RNG.setstate(rand_state)


def _monkeypatch_random(seed: Optional[int] = None, cuda_deterministic: bool = False):
    '''
    https://pytorch.org/docs/stable/notes/randomness.html

    We cannot recover the previous state.
    It is because torch / np does not provide such functions for GPU or for np.Generator,
    and some of their RNG code are in C. We cannnot simply monkeypatch the python part.

    Our strategy is:
    1. setting a list of random seed from CPU (usually based on MT19997) as meta_data_state.
    2. monkeypatch the random seed every N epochs.

    params:
      seed: the seed generated from _META_RNG.
      cuda_deterministic: whether to use deterministic cuda.
    '''
    global THE_SEED
    global NP_SEED
    global TORCH_SEED
    if seed is None:
        THE_SEED = None
        NP_SEED = None
        TORCH_SEED = None
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.deterministic = False
        return

    np_seed = seed % _NP_MAX_SEED_RANGE
    torch_seed = seed % _TORCH_MAX_SEED_RANGE
    random.seed(seed)
    np.random.seed(np_seed)
    torch.manual_seed(torch_seed)

    THE_SEED = seed
    NP_SEED = np_seed
    TORCH_SEED = torch_seed

    if cuda_deterministic:
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
    else:
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.deterministic = False


def _get_seed(seed_range: int = _DEFAULT_META_RAND_RANGE) -> int:
    global _SEED

    assert _META_RNG is not None, f'_META_RNG is None'

    _SEED = _META_RNG.randrange(seed_range)

    return _SEED