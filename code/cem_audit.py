"""Human audit sheet for the CEM augmentation (owner rule: audit constructed data vs gold).

Samples N views per manipulated view type (V1 kill, V2 distractor, V3 swap, V4 relocate,
V6 inject) from the TRAIN fit split with a fixed seed, and writes:
  results/cem_audit/audit_sheet.csv   one row per view: original paragraph, edited text, the
                                      technique(s) the rule claims, and empty columns for the
                                      annotator (label_correct yes/no, fluent yes/no, note)
  results/cem_audit/audit_key.json    view metadata (hidden from the annotator)
After annotation, `--score` reads the filled CSV and reports per view type the share of
correct label targets and fluent texts, with Wilson 95% intervals.

The annotator judges the EDITED text only against the SemEval-2023 technique definitions:
"Does this text contain <technique>?" for the claimed technique (and, for V3, whether the old
technique is gone). Row order is shuffled so view types are not grouped.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import augment as A  # noqa: E402
import data as D  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "results" / "cem_audit"
KINDS = ("V1", "V2", "V3", "V4", "V6")
V2_KINDS = ("KILL", "INJECT", "SWAP", "KILL_C", "INJECT_C", "SWAP_C")


def question(v: dict) -> str:
    k = v["view"]
    if k in V2_KINDS:
        if k == "KILL":
            return f"Is {v['tech']} ABSENT from the edited text?"
        if k == "INJECT":
            return f"Is {v['tech']} PRESENT in the edited text?"
        if k == "SWAP":
            return f"Is {v['tech2']} PRESENT and {v['tech']} ABSENT in the edited text?"
        return ("Are the techniques unchanged by the edit? Original techniques: "
                + (", ".join(A.techs_of(v["label"])) or "none"))
    if k == "V1":
        want = "PRESENT" if v["label"][A.LAB2ID[v["tech"]]] > 0.5 else "ABSENT"
        return f"Is {v['tech']} {want} in the edited text?"
    if k == "V2":
        return "Are all original techniques still present, unchanged? (" + \
            ", ".join(A.techs_of(v["label"])) + ")"
    if k == "V3":
        gone = "absent" if v["label"][A.LAB2ID[v["tech"]]] < 0.5 else "still present"
        return f"Is {v['tech2']} PRESENT and {v['tech']} {gone}?"
    if k == "V4":
        return f"Is {v['tech']} still PRESENT after moving its span?"
    return f"Is {v['tech']} PRESENT in the edited text?"


def wilson(k: int, n: int):
    if n == 0:
        return (float("nan"), float("nan"))
    p, z = k / n, 1.96
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 3), round(c + h, 3))


def make(n_per: int, seed: int) -> None:
    rng = random.Random(seed)
    recs = D.load(D.TRAIN_ALL)
    fit, _ = D.split_by_article(recs)
    pool = A.build_pool(fit)
    by_id = {r["id"]: r for r in fit}
    views = D.epoch_views(fit, pool, random.Random(seed))
    rows, key = [], []
    for kind in KINDS:
        cand = [v for v in views if v["view"] == kind]
        for v in rng.sample(cand, min(n_per, len(cand))):
            orig = by_id.get(v["id"], {}).get("paragraph_text", "") if v["id"] != "inject" else ""
            rows.append({"view_id": "", "original": orig, "edited": v["text"],
                         "question": question(v), "label_correct": "", "fluent": "", "note": ""})
            key.append({"view": kind, "tech": v.get("tech"), "tech2": v.get("tech2"),
                        "label": A.techs_of(v["label"]), "why": v.get("why")})
    order = list(range(len(rows)))
    rng.shuffle(order)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "audit_sheet.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for n, k in enumerate(order):
            rows[k]["view_id"] = n
            w.writerow(rows[k])
    (OUT / "audit_key.json").write_text(json.dumps([key[k] for k in order], indent=1))
    print(f"wrote {len(rows)} rows to {OUT / 'audit_sheet.csv'}")


def make_v2(n_evid: int, n_ctrl: int, seed: int) -> None:
    """Sample the FROZEN v2 pool (exactly what training uses): n_evid per evidence family and
    n_ctrl per control family, shuffled; separate files (audit_v2_*)."""
    rng = random.Random(seed)
    pool = [json.loads(l) for l in (D.ROOT / "data" / "cem_v2_pool.jsonl").open(encoding="utf-8")]
    by_pair = {}
    for v in pool:
        by_pair.setdefault(v["pair"], []).append(v)
    D.fill_tech2(by_pair.values())
    orig = {r["id"]: r["paragraph_text"] for r in D.load(D.TRAIN_ALL)}
    rows, key = [], []
    for kind in V2_KINDS:
        cand = [v for v in pool if v["view"] == kind]
        n = n_evid if not kind.endswith("_C") else n_ctrl
        for v in rng.sample(cand, min(n, len(cand))):
            rows.append({"view_id": "", "original": orig.get(v["orig_id"], ""), "edited": v["text"],
                         "question": question(v), "label_correct": "", "fluent": "", "note": ""})
            key.append({"view": kind, "tech": v.get("tech"), "tech2": v.get("tech2"),
                        "label": A.techs_of(v["label"]), "why": v.get("why"), "pair": v["pair"],
                        "dnll": v.get("dnll")})
    order = list(range(len(rows)))
    rng.shuffle(order)
    with (OUT / "audit_v2_sheet.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for n, k in enumerate(order):
            rows[k]["view_id"] = n
            w.writerow(rows[k])
    (OUT / "audit_v2_key.json").write_text(json.dumps([key[k] for k in order], indent=1))
    print(f"wrote {len(rows)} rows to {OUT / 'audit_v2_sheet.csv'}")


def score(prefix: str = "audit", kinds=KINDS, tag: str = "") -> None:
    """tag: score a variant sheet `{prefix}_sheet{tag}.csv` (e.g. "_claude", an AI
    pre-annotation) into `{prefix}_scores{tag}.json` / `soft_targets{tag}.json`, so it never
    overwrites the human audit's outputs."""
    key = json.loads((OUT / f"{prefix}_key.json").read_text())
    with (OUT / f"{prefix}_sheet{tag}.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    res = {}
    for kind in kinds:
        rs = [r for r, k in zip(rows, key) if k["view"] == kind and r["label_correct"].strip()]
        ok = sum(r["label_correct"].strip().lower().startswith("y") for r in rs)
        fl = sum(r["fluent"].strip().lower().startswith("y") for r in rs)
        res[kind] = {"n": len(rs), "label_correct": ok / max(1, len(rs)),
                     "label_ci95": wilson(ok, len(rs)), "fluent": fl / max(1, len(rs)),
                     "fluent_ci95": wilson(fl, len(rs))}
    (OUT / f"{prefix}_scores{tag}.json").write_text(json.dumps(res, indent=2))
    if prefix == "audit_v2":
        # soft targets for training (--soft-json): audited validity per EVIDENCE family,
        # only for families that pass the 0.8 bar; controls keep hard targets
        soft = {k: round(v["label_correct"], 3) for k, v in res.items()
                if not k.endswith("_C") and v["n"] >= 20 and v["label_correct"] >= 0.8}
        (OUT / f"soft_targets{tag}.json").write_text(json.dumps(soft, indent=2))
        dropped = [k for k, v in res.items() if not k.endswith("_C") and v["label_correct"] < 0.8]
        print("soft targets:", soft, "families below 0.8 (drop from training):", dropped)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-per", type=int, default=30)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--v2", action="store_true", help="sample / score the frozen CEM v2 pool")
    ap.add_argument("--tag", default="", help="score a variant sheet, e.g. _claude")
    a = ap.parse_args()
    if a.v2:
        score("audit_v2", V2_KINDS, a.tag) if a.score else make_v2(40, 15, a.seed)
    else:
        score(tag=a.tag) if a.score else make(a.n_per, a.seed)
