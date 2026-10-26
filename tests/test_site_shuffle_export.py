import json

import numpy as np
import pytest
from src.nulls.pools import pool_a, pool_b
from src.search.real import literal_table
from src.site.export_shuffle import export_shuffle, python_result


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    d = tmp_path_factory.mktemp("shuffle")
    info = export_shuffle(d / "pub", d / "data", d / "fix")
    return d, info


def unpack(raw: bytes):
    n = int(np.frombuffer(raw[:4], dtype="<u4")[0])
    vecs = np.frombuffer(raw[4:4 + 4 * n], dtype="<u4")
    flags = np.frombuffer(raw[4 + 4 * n:4 + 5 * n], dtype=np.uint8)
    return n, vecs, flags


def test_pool_bin_matches_pool_b_and_pool_a(out):
    d, info = out
    n, vecs, flags = unpack((d / "pub" / "pool.bin").read_bytes())
    VB, VA = pool_b(), pool_a()
    assert n == len(VB) == info["n_vectors"] == 15010 and int(flags.sum()) == len(VA) == 266
    rows = ((vecs[:, None] >> np.arange(32, dtype=np.uint32)) & 1).astype(bool)
    assert (rows == VB).all()
    in_a = {v.tobytes() for v in VA}
    assert all(bool(flags[i]) == (VB[i].tobytes() in in_a) for i in range(n))


def test_meta_ids_resolve_to_their_vectors(out):
    d, _ = out
    meta = json.loads((d / "pub" / "pool_meta.json").read_text())
    VB, table = pool_b(), literal_table()
    assert len(meta["ids"]) == len(set(meta["ids"])) == len(VB)
    for i in (0, 1, 500, 7000, 15009):
        assert meta["ids"][i] in {a["id"] for a in table[VB[i].tobytes()]}
    assert all(i in meta["gloss"] for i in meta["ids"] if "astro_geo_" not in i)


def test_goldens_cover_none_tier_1a_and_tier_1b(out):
    d, _ = out
    g = json.loads((d / "fix" / "goldens.json").read_text())
    assert len(g) == 303
    for tgt in ("T1", "T2", "T3"):
        labs = [c["python_label"] for c in g if c["source"] == f"null_{tgt}"]
        assert labs.count("conjA") == 12 and labs.count("none") == 12 and labs.count("conjB") == 76
    real = {c["id"]: c["python_label"] for c in g if c["source"] == "real"}
    assert real == {"real:T1": "conjB", "real:T2": "none", "real:T3": "conjB"}
    # a sample recomputes to the stored Python result
    VA, VB = pool_a(), pool_b()
    for c in g[::37]:
        t = ((c["target"] >> np.arange(32)) & 1).astype(bool)
        r = python_result(t, VA, VB)
        assert r["label"] == c["python_label"] and r["min_k"] == c["min_k"] and r["candidates_B"] == c["candidates_B"]


def test_real_targets_in_shuffle_json(out):
    d, _ = out
    s = json.loads((d / "data" / "shuffle.json").read_text())
    assert [s["real"][k]["n_true"] for k in ("T1", "T2", "T3")] == [18, 15, 17]
    assert s["real_labels"] == {"T1": "conjB", "T2": "none", "T3": "conjB"}
