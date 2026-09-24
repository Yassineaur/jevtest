"""Seed check of the headline: CEM v2 effect on the plain model (T0+CEMv2 minus T0), seeds 0-2.

For each seed, compare.compare() gives the paired effect on dev (micro-F1 and the v2
faithfulness families). Across seeds: mean, standard deviation and range. The effect is taken
as robust at this stage only if every seed's 95% CI excludes 0 in the same direction and the
across-seed spread is small relative to the mean. Writes results/seedcheck.json and .md.
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compare import compare  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PAIRS = {0: (ROOT / "results/cemv2/T0v2_s0", ROOT / "results/ablation/T0nc_s0"),
         1: (ROOT / "results/seedcheck/T0v2_s1", ROOT / "results/seedcheck/T0nc_s1"),
         2: (ROOT / "results/seedcheck/T0v2_s2", ROOT / "results/seedcheck/T0nc_s2")}
FAMS = ("KILL", "INJECT", "SWAP", "RELOC", "SUFF")


def main() -> None:
    per = {}
    for s, (a, b) in PAIRS.items():
        if not (a / "eval" / "metrics.json").exists() or not (b / "eval" / "metrics.json").exists():
            continue
        c = compare(a, b)
        row = {"micro_f1": (c["micro_f1"]["diff"], c["micro_f1"]["diff_ci95"]),
               "f1_a": c["micro_f1"]["a"], "f1_b": c["micro_f1"]["b"]}
        for f in FAMS:
            v = c["faithfulness_v2"].get(f)
            if v:
                row[f] = (v["a_minus_b"], v["a_minus_b_ci95"])
        per[s] = row
    summ = {}
    for k in ("micro_f1",) + FAMS:
        xs = [per[s][k][0] for s in per if k in per[s]]
        if xs:
            summ[k] = {"mean": st.mean(xs), "sd": st.stdev(xs) if len(xs) > 1 else None,
                       "min": min(xs), "max": max(xs), "n_seeds": len(xs),
                       "all_ci_exclude_0_same_sign": all(
                           (per[s][k][1][0] > 0) == (xs[0] > 0) and
                           (per[s][k][1][0] > 0 or per[s][k][1][1] < 0) for s in per if k in per[s])}
    (ROOT / "results" / "seedcheck.json").write_text(json.dumps({"per_seed": per, "summary": summ}, indent=2))
    L = ["# Seed check: CEM v2 effect on the plain model (T0+CEMv2 - T0), dev", "",
         "| Seed | F1 T0+CEMv2 / T0 | dF1 | KILL | INJECT | SWAP | RELOC* | SUFF* |", "|---|---|---|---|---|---|---|---|"]
    fmt = lambda v: f"{v[0]:+.3f} [{v[1][0]:+.3f}, {v[1][1]:+.3f}]"  # noqa: E731
    for s, r in per.items():
        L.append(f"| {s} | {r['f1_a']:.3f} / {r['f1_b']:.3f} | {fmt(r['micro_f1'])} | "
                 + " | ".join(fmt(r[f]) if f in r else "-" for f in FAMS) + " |")
    L += ["", "| Across seeds | mean | sd | min | max | every seed's CI excludes 0, same sign |", "|---|---|---|---|---|---|"]
    for k, v in summ.items():
        sd = "-" if v["sd"] is None else f"{v['sd']:.3f}"
        L.append(f"| {k} | {v['mean']:+.3f} | {sd} | {v['min']:+.3f} | {v['max']:+.3f} | {v['all_ci_exclude_0_same_sign']} |")
    (ROOT / "results" / "seedcheck.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
