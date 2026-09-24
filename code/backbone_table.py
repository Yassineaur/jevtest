"""Apply the pre-registered backbone rule (MVP_PLAN.md) and write results/backbone_table.md.

Per backbone, pick the learning rate with the best TRAIN-HOLDOUT micro-F1 (never dev). Across
backbones, take the best holdout F1 unless a faster backbone is within 0.01 of it, in which case
take the faster one. Dev F1, evidence hit and idle-GPU latency are reported, not used to choose.
Latency comes from results/latency_ours.json (idle GPU) when present, else it is left blank.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRID = {
    "microsoft/deberta-v3-base": [("2e-5", ROOT / "results/pilot/T4_s0"),
                                  ("4e-5", ROOT / "results/backbone/debB_lr4e5")],
    "answerdotai/ModernBERT-base": [("3e-5", ROOT / "results/backbone/mbB_lr3e5"),
                                    ("6e-5", ROOT / "results/backbone/mbB_lr6e5")],
    "microsoft/deberta-v3-large": [("1e-5", ROOT / "results/backbone/debL_lr1e5"),
                                   ("2e-5", ROOT / "results/backbone/debL_lr2e5")],
}
PARAMS_M = {"microsoft/deberta-v3-base": 184, "answerdotai/ModernBERT-base": 149,
            "microsoft/deberta-v3-large": 434}


def main() -> None:
    lat = {}
    lp = ROOT / "results" / "latency_ours.json"
    if lp.exists():
        for k, v in json.loads(lp.read_text()).items():
            lat[str(Path(k).resolve())] = v
    rows, chosen = [], {}
    for bb, runs in GRID.items():
        best = None
        for lr, d in runs:
            done = d / "DONE"
            if not done.exists():
                rows.append({"backbone": bb, "lr": lr, "status": "missing"})
                continue
            hold = json.loads(done.read_text())["best_holdout_f1"]
            m = json.loads((d / "eval" / "metrics.json").read_text())
            L = lat.get(str((d / "best.pt").resolve()), {})
            r = {"backbone": bb, "lr": lr, "holdout_f1": hold, "dev_f1": m["label_mode"]["micro_f1"],
                 "dev_span_f1": m.get("span_mode", {}).get("micro_f1"),
                 "top1_hit": m.get("evidence", {}).get("top1_hit"),
                 "p50_ms": L.get("p50_ms"), "para_per_s": L.get("throughput_para_per_s_bs32"),
                 "run": str(d.relative_to(ROOT))}
            rows.append(r)
            if best is None or hold > best["holdout_f1"]:
                best = r
        if best:
            chosen[bb] = best
    pick = None
    if chosen:
        top = max(chosen.values(), key=lambda r: r["holdout_f1"])
        speed = lambda r: (r["p50_ms"] if r["p50_ms"] is not None else PARAMS_M[r["backbone"]])  # noqa: E731
        near = [r for r in chosen.values() if r["holdout_f1"] >= top["holdout_f1"] - 0.01]
        pick = min(near, key=speed)
    out = {"rows": rows, "per_backbone_choice": chosen, "selected": pick,
           "rule": "best holdout F1 per backbone; across backbones the fastest within 0.01 of the best"}
    (ROOT / "results" / "backbone_table.json").write_text(json.dumps(out, indent=2))
    f = lambda x, n=3: "-" if x is None else f"{x:.{n}f}"  # noqa: E731
    L = ["# Backbone pilot (T4 recipe, CEM v1, seed 0)", "",
         "Rule pre-registered in MVP_PLAN.md: choose on TRAIN-HOLDOUT F1; dev and latency reported only.", "",
         "| Backbone | Params | LR | holdout F1 | dev F1 | dev span F1 | top-1 hit | p50 ms (idle) | para/s bs32 |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r.get("status") == "missing":
            L.append(f"| {r['backbone']} | {PARAMS_M[r['backbone']]}M | {r['lr']} | (not run) |  |  |  |  |  |")
            continue
        mark = " **(chosen per backbone)**" if chosen.get(r["backbone"]) is r else ""
        L.append(f"| {r['backbone']}{mark} | {PARAMS_M[r['backbone']]}M | {r['lr']} | {f(r['holdout_f1'])} | "
                 f"{f(r['dev_f1'])} | {f(r['dev_span_f1'])} | {f(r['top1_hit'])} | {f(r['p50_ms'], 1)} | "
                 f"{f(r['para_per_s'], 0)} |")
    if pick:
        L += ["", f"Selected by the rule: **{pick['backbone']} at lr {pick['lr']}** (holdout {pick['holdout_f1']:.3f})."]
    (ROOT / "results" / "backbone_table.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
