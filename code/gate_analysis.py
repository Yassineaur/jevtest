"""Does the coupled parser learn the discourse-evidence link the data shows? (pre-stated test)

Prediction written in notes/parser_design.md BEFORE training: techniques whose gold spans are
whole runs of EDUs far above chance (Doubt, Causal Oversimplification, Appeal to Authority,
False Dilemma, ...) get larger learned gates (a_t start, b_t end) than lexical techniques
(Loaded Language, Name Calling).

Test: Spearman rank correlation between the learned gate (a_t + b_t) and the chance-adjusted
alignment (gold 'both' rate minus chance 'both' rate, results/discourse_alignment.json), over the
19 techniques, with an exact-enough permutation p-value (20,000 shuffles). Writes
results/gate_analysis.json.
Usage: python code/gate_analysis.py results/parser/T4disc_s0/eval/metrics.json
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x, y):
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den


def main() -> None:
    m = json.loads(Path(sys.argv[1]).read_text())
    align = json.loads((ROOT / "results" / "discourse_alignment.json").read_text())["per_technique"]
    techs = [t for t in m["gates"] if t in align and align[t]["chance"]]
    gate = [sum(m["gates"][t]) for t in techs]
    excess = [align[t]["gold"]["both"] - align[t]["chance"]["both"] for t in techs]
    rho = spearman(gate, excess)
    rng = random.Random(0)
    n_ge = 0
    for _ in range(20000):
        g = gate[:]
        rng.shuffle(g)
        n_ge += spearman(g, excess) >= rho
    rows = sorted(({"technique": t, "gate_sum": round(g, 4), "alignment_excess": round(e, 4)}
                   for t, g, e in zip(techs, gate, excess)), key=lambda r: -r["gate_sum"])
    res = {"source": sys.argv[1], "n_techniques": len(techs), "spearman": rho,
           "p_one_sided": (n_ge + 1) / 20001, "rows": rows}
    (ROOT / "results" / "gate_analysis.json").write_text(json.dumps(res, indent=2))
    print(f"Spearman(gate, alignment excess) = {rho:.3f}, one-sided permutation p = {res['p_one_sided']:.4f}")
    for r in rows:
        print(f"  {r['technique']:34s} gate {r['gate_sum']:+.3f}  excess {r['alignment_excess']:+.3f}")


if __name__ == "__main__":
    main()
