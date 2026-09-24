"""Paired comparison of two evaluated runs (e.g. T4 vs T0) on dev, with bootstrap CIs.

Reads <run>/eval/metrics.json, preds_dev.jsonl and faith_cases.jsonl for both runs.
  - micro-F1 difference (each run at its own holdout-tuned threshold), paired bootstrap over dev
    paragraphs;
  - faithfulness difference-in-differences: per (paragraph, technique) with both a kill and a
    matched control erase, d = delta_kill - delta_ctrl; compares d between runs (paired);
  - distractor and relocation invariance (mean |delta|), paired.
Writes <out>.json and prints a short table.

Run: ..\\torch_env\\Scripts\\python.exe code\\compare.py results\\pilot\\T4_s0 results\\pilot\\T0_s0
       --out results\\pilot\\compare_T4_vs_T0_s0
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from augment import ENGLISH_19  # noqa: E402

B = 2000


def load_jsonl(p: Path):
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]


def boot_ci(stat, n, seed=0):
    rng = np.random.default_rng(seed)
    vals = [stat(rng.integers(0, n, n)) for _ in range(B)]
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def micro_counts(p, y, th):
    pred, gold = p >= th, y > 0.5
    return ((pred & gold).sum(1), (pred & ~gold).sum(1), (~pred & gold).sum(1))


def f1_from(tp, fp, fn):
    return 2 * tp.sum() / max(1.0, 2 * tp.sum() + fp.sum() + fn.sum())


def kill_dd(rows, kind="kill", ctrl="kill_ctrl"):
    """key -> delta_<kind> - delta_<ctrl> for cases that have both."""
    k = {r["key"]: r["delta"] for r in rows if r["kind"] == kind}
    c = {r["key"]: r["delta"] for r in rows if r["kind"] == ctrl}
    return {key: k[key] - c[key] for key in k if key in c}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a", type=Path, help="treatment run dir (e.g. T4)")
    ap.add_argument("b", type=Path, help="control run dir (e.g. T0)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    res = compare(a.a, a.b)
    a.out.with_suffix(".json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


def compare(dir_a: Path, dir_b: Path) -> dict:
    """All paired contrasts between two evaluated runs (a = treatment, b = control)."""
    a = argparse.Namespace(a=Path(dir_a), b=Path(dir_b))
    ma = json.loads((a.a / "eval" / "metrics.json").read_text())
    mb = json.loads((a.b / "eval" / "metrics.json").read_text())
    pa, pb = load_jsonl(a.a / "eval" / "preds_dev.jsonl"), load_jsonl(a.b / "eval" / "preds_dev.jsonl")
    assert [r["id"] for r in pa] == [r["id"] for r in pb], "dev order differs"
    idx = {t: i for i, t in enumerate(ENGLISH_19)}
    y = np.zeros((len(pa), len(ENGLISH_19)))
    for k, r in enumerate(pa):
        for t in r["gold"]:
            y[k, idx[t]] = 1
    Pa, Pb = np.array([r["p"] for r in pa]), np.array([r["p"] for r in pb])
    ca = micro_counts(Pa, y, ma["label_mode"]["threshold"])
    cb = micro_counts(Pb, y, mb["label_mode"]["threshold"])
    diff = lambda s: f1_from(*(c[s] for c in ca)) - f1_from(*(c[s] for c in cb))  # noqa: E731
    allr = np.arange(len(pa))
    res = {"a": str(a.a), "b": str(a.b),
           "micro_f1": {"a": float(f1_from(*ca)), "b": float(f1_from(*cb)),
                        "diff": float(diff(allr)), "diff_ci95": boot_ci(diff, len(pa))}}

    fa, fb = load_jsonl(a.a / "eval" / "faith_cases.jsonl"), load_jsonl(a.b / "eval" / "faith_cases.jsonl")
    da, db = kill_dd(fa), kill_dd(fb)
    keys = sorted(set(da) & set(db))
    if keys:
        va, vb = np.array([da[k] for k in keys]), np.array([db[k] for k in keys])
        d = va - vb  # more negative = a's label falls more when evidence (not control) is erased
        res["kill_minus_ctrl"] = {"n": len(keys), "a": float(va.mean()), "b": float(vb.mean()),
                                  "a_minus_b": float(d.mean()),
                                  "a_minus_b_ci95": boot_ci(lambda s: d[s].mean(), len(d)),
                                  "a_ci95": boot_ci(lambda s: va[s].mean(), len(va))}
    va_path, vb_path = a.a / "eval" / "faith_v2_pairs.jsonl", a.b / "eval" / "faith_v2_pairs.jsonl"
    if va_path.exists() and vb_path.exists():
        ra = {r["pair"]: r for r in load_jsonl(va_path)}
        rb = {r["pair"]: r for r in load_jsonl(vb_path)}
        res["faithfulness_v2"] = {}
        for fam in ("KILL", "INJECT", "SWAP", "RELOC", "SUFF"):
            ks = sorted(k for k in set(ra) & set(rb) if ra[k]["family"] == fam)
            if not ks:
                continue
            xa = np.array([ra[k]["stat"] for k in ks])
            xb = np.array([rb[k]["stat"] for k in ks])
            d = xa - xb
            res["faithfulness_v2"][fam] = {
                "n": len(ks), "a": float(xa.mean()), "b": float(xb.mean()),
                "a_ci95": boot_ci(lambda s: xa[s].mean(), len(xa)),
                "b_ci95": boot_ci(lambda s: xb[s].mean(), len(xb)),
                "a_minus_b": float(d.mean()), "a_minus_b_ci95": boot_ci(lambda s: d[s].mean(), len(d))}
    ia, ib = kill_dd(fa, "inject", "inject_ctrl"), kill_dd(fb, "inject", "inject_ctrl")
    keys = sorted(set(ia) & set(ib))
    if keys:
        va, vb = np.array([ia[k] for k in keys]), np.array([ib[k] for k in keys])
        d = va - vb  # more positive = a reacts more to the technique than to insertion itself
        res["inject_minus_ctrl"] = {"n": len(keys), "a": float(va.mean()), "b": float(vb.mean()),
                                    "a_ci95": boot_ci(lambda s: va[s].mean(), len(va)),
                                    "b_ci95": boot_ci(lambda s: vb[s].mean(), len(vb)),
                                    "a_minus_b": float(d.mean()),
                                    "a_minus_b_ci95": boot_ci(lambda s: d[s].mean(), len(d))}
    for kind in ("distractor", "relocate", "inject"):
        ra = {r["case"]: r["delta"] for r in fa if r["kind"] == kind}
        rb = {r["case"]: r["delta"] for r in fb if r["kind"] == kind}
        ks = sorted(set(ra) & set(rb))
        if ks:
            xa, xb = np.array([ra[k] for k in ks]), np.array([rb[k] for k in ks])
            stat = (np.abs(xa) - np.abs(xb)) if kind != "inject" else (xa - xb)
            res[kind] = {"n": len(ks), "a": float((np.abs(xa) if kind != "inject" else xa).mean()),
                         "b": float((np.abs(xb) if kind != "inject" else xb).mean()),
                         "a_minus_b": float(stat.mean()),
                         "a_minus_b_ci95": boot_ci(lambda s: stat[s].mean(), len(stat))}
    return res


if __name__ == "__main__":
    main()
