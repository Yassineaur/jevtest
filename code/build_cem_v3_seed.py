"""Assemble the CEM v3 seed set: whole-unit rewrites of 100 training paragraphs.

Inputs (data/cem_v3_seed/):
  seed_paragraphs.json   100 train-fit paragraphs rebuilt from the v1/v2 audit sheets, with their
                         gold paragraph-level techniques and sentence units
  rewrites_b*.py         the rewrites, as (pid, family, tech, {unit: new_text}, why)
Outputs:
  seed_views.jsonl       one line per view: text, 19-dim label, family, tech, pair id, rationale
  seed_stats.json        counts per family and technique
  results/cem_audit/audit_v3_seed_sheet.csv + audit_v3_seed_key.json   blind audit sample

Families (each edit has a matched control that rewrites the SAME units):
  KILL   rewrite every unit carrying `tech` so it is gone      label = gold - {tech}
  KILL_C rewrite the same units, technique kept               label = gold
  INJECT rewrite one unit so it carries `tech`                 label = gold + {tech}
  INJECT_C rewrite the same unit neutrally                    label = gold
The rewrites were written by an AI model (Claude) and are NOT yet human-audited.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "cem_v3_seed"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import augment as A  # noqa: E402

FAMILIES = ("KILL", "KILL_C", "INJECT", "INJECT_C")


def load_rewrites():
    out = []
    for f in sorted(SEED.glob("rewrites_b*.py")):
        spec = importlib.util.spec_from_file_location(f.stem, f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        out += mod.R
    return out


def apply(text: str, units: list, edits: dict) -> str:
    """Replace whole units inside the original text (keeps the original spacing)."""
    for k, new in edits.items():
        old = units[k]
        assert old in text, f"unit not found: {old[:60]}"
        text = text.replace(old, new, 1)
    return text


def main() -> None:
    paras = {p["pid"]: p for p in json.loads((SEED / "seed_paragraphs.json").read_text())}
    rw = load_rewrites()
    views, errors = [], []
    by_key = {}
    for pid, fam, tech, edits, why in rw:
        p = paras[pid]
        assert fam in FAMILIES, fam
        assert tech in A.LAB2ID, tech
        gold = set(p["techs"])
        if fam == "KILL" and tech not in gold:
            errors.append(f"{pid} KILL of absent {tech}")
        if fam == "INJECT" and tech in gold:
            errors.append(f"{pid} INJECT of present {tech}")
        bad = [k for k in edits if k >= len(p["units"])]
        if bad:
            errors.append(f"{pid} bad unit index {bad}")
            continue
        lab = gold - {tech} if fam == "KILL" else gold | {tech} if fam == "INJECT" else gold
        pair = f"{pid}:{fam.rstrip('_C')}:{tech}"
        by_key.setdefault(pair, {})[fam] = sorted(edits)
        views.append({"pid": pid, "pair": pair, "view": fam, "tech": tech,
                      "text": apply(p["text"], p["units"], edits), "orig": p["text"],
                      "label": A.label_vector(sorted(lab)), "why": why,
                      "units": sorted(edits), "author": "claude (AI), unaudited"})
    # every edit needs its control on the same units
    for pair, fams in by_key.items():
        base = pair.split(":")[1]
        if set(fams) != {base, base + "_C"}:
            errors.append(f"{pair} unmatched: {sorted(fams)}")
        elif fams[base] != fams[base + "_C"]:
            errors.append(f"{pair} control edits different units")
    if errors:
        raise SystemExit("ERRORS:\n" + "\n".join(errors))
    with (SEED / "seed_views.jsonl").open("w", encoding="utf-8") as f:
        for v in views:
            f.write(json.dumps(v, ensure_ascii=False) + "\n")
    stats = {"paragraphs_used": len({v["pid"] for v in views}), "views": len(views),
             "pairs": len(by_key), "by_family": Counter(v["view"] for v in views),
             "by_family_tech": {fam: Counter(v["tech"] for v in views if v["view"] == fam)
                                for fam in ("KILL", "INJECT")}}
    (SEED / "seed_stats.json").write_text(json.dumps(stats, indent=1))
    # blind audit sheet: every view, shuffled, with the same question style as the v2 audit
    rng = random.Random(11)
    order = list(range(len(views)))
    rng.shuffle(order)
    out = ROOT / "results" / "cem_audit"
    with (out / "audit_v3_seed_sheet.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["view_id", "original", "edited", "question",
                                          "label_correct", "fluent", "note"])
        w.writeheader()
        for n, k in enumerate(order):
            v = views[k]
            if v["view"] == "KILL":
                q = f"Is {v['tech']} ABSENT from the edited text?"
            elif v["view"] == "INJECT":
                q = f"Is {v['tech']} PRESENT in the edited text?"
            else:
                q = ("Are the techniques unchanged by the edit? Original techniques: "
                     + (", ".join(sorted(paras[v['pid']]['techs'])) or "none"))
            w.writerow({"view_id": n, "original": v["orig"], "edited": v["text"], "question": q,
                        "label_correct": "", "fluent": "", "note": ""})
    (out / "audit_v3_seed_key.json").write_text(json.dumps(
        [{"view": views[k]["view"], "tech": views[k]["tech"], "tech2": None,
          "label": A.techs_of(views[k]["label"]), "pair": views[k]["pair"]} for k in order], indent=1))
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
