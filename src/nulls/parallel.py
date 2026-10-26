"""Deterministic chunked parallelism: results depend on (seed, chunk size), not on worker count."""

from __future__ import annotations

import multiprocessing as mp
from collections.abc import Callable

import numpy as np

_STATE: dict = {}


def _init(initializer: Callable | None, args: tuple) -> None:
    if initializer:
        _STATE.update(initializer(*args))


def _run(job: tuple):
    fn, idx, n, entropy, spawn_n, params = job
    rng = np.random.default_rng(np.random.SeedSequence(entropy).spawn(spawn_n)[idx])
    return idx, fn(rng, n, _STATE, params)


def run_chunks(fn: Callable, total: int, chunk: int, entropy: int, params: dict | None = None,
               initializer: Callable | None = None, init_args: tuple = (), workers: int = 16) -> list:
    """fn(rng, n, state, params) -> list of records (fn must be a module-level function). Chunk i uses SeedSequence(entropy).spawn(n_chunks)[i]."""
    sizes = [chunk] * (total // chunk) + ([total % chunk] if total % chunk else [])
    jobs = [(fn, i, n, entropy, len(sizes), params or {}) for i, n in enumerate(sizes)]
    ctx = mp.get_context("fork")
    with ctx.Pool(workers, initializer=_init, initargs=(initializer, init_args)) as pool:
        res = pool.map(_run, jobs, chunksize=1)
    res.sort(key=lambda r: r[0])
    return [rec for _, recs in res for rec in recs]


def _run_item(job: tuple):
    fn, idx, item, params = job
    return idx, fn(item, _STATE, params)


def run_items(fn: Callable, items: list, params: dict | None = None, initializer: Callable | None = None,
              init_args: tuple = (), workers: int = 16) -> list:
    """fn(item, state, params) -> record; results returned in item order (no randomness involved)."""
    jobs = [(fn, i, it, params or {}) for i, it in enumerate(items)]
    ctx = mp.get_context("fork")
    with ctx.Pool(workers, initializer=_init, initargs=(initializer, init_args)) as pool:
        res = pool.map(_run_item, jobs, chunksize=1)
    res.sort(key=lambda r: r[0])
    return [r for _, r in res]
