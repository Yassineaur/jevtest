"""Do persuasion evidence spans coincide with discourse units? (no GPU, read-only inputs)

Replicates the span-EDU alignment analysis of Chernyavskiy, Ilvovsky & Nakov (EACL 2024,
Table 6) with the owner's cached DMRST parses (../semeval/data/en/rst_cache/, one JSON per
article, EDU leaves with article-level char offsets) and the official span gold
(../semeval/data/en/{split}-labels-subtask-3-spans/). Adds what their table lacks: a matched
CHANCE control (the same-length span placed at a random position inside the same paragraph),
because a long span overlaps EDUs heavily whatever its position.

Per technique:
  cover_iou   span length / total length of the EDUs it overlaps (their mIoU definition)
  start_edu   span start within TOL chars of an EDU start
  end_edu     span end within TOL chars of an EDU end
  both        start_edu and end_edu (the span is a whole sequence of EDUs)
each for gold and for the chance control, plus the median span length in characters.

Articles where the parser fell back (used_fallback) are excluded and counted.
Writes results/discourse_alignment.json.
"""
from __future__ import annotations

import json
import random
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EN = ROOT.parent / "semeval" / "data" / "en"
TOL = 2  # chars of slack for punctuation and spaces at EDU edges


def load_spans(split: str):
    out = {}
    for f in (EN / f"{split}-labels-subtask-3-spans").glob("article*-labels-subtask-3.txt"):
        aid = f.name[len("article"):].split("-")[0]
        rows = []
        for line in f.read_text(encoding="utf-8").splitlines():
            p = line.split("\t")
            if len(p) >= 4:
                rows.append((p[1].strip(), int(p[2]), int(p[3])))
        out[aid] = rows
    return out


def line_ranges(text: str):
    rows, cur = [], 0
    for raw in text.splitlines(keepends=True):
        body = raw.rstrip("\r\n")
        if body.strip():
            rows.append((cur, cur + len(body)))
        cur += len(raw)
    return rows


def metrics(a: int, b: int, edus):
    over = [(s, e) for s, e in edus if e > a and s < b]
    if not over:
        return None
    cover = sum(e - s for s, e in over)
    starts = [s for s, _ in edus]
    ends = [e for _, e in edus]
    st_ok = min(abs(a - s) for s in starts) <= TOL
    en_ok = min(abs(b - e) for e in ends) <= TOL
    return (b - a) / max(1, cover), st_ok, en_ok


def main() -> None:
    rng = random.Random(0)
    per = {}
    n_fallback = n_articles = 0
    for split in ("train", "dev"):
        spans = load_spans(split)
        for aid, rows in spans.items():
            cache = EN / "rst_cache" / f"{split}_{aid}.json"
            if not cache.exists():
                continue
            d = json.loads(cache.read_text(encoding="utf-8"))
            if d.get("used_fallback"):
                n_fallback += 1
                continue
            n_articles += 1
            text = d["text"]
            edus = sorted((l["char_start"], l["char_end"]) for l in d["leaves"])
            lines = line_ranges(text)
            for tech, a, b in rows:
                # trim whitespace at span edges (annotators sometimes include it)
                while a < b and text[a].isspace():
                    a += 1
                while b > a and text[b - 1].isspace():
                    b -= 1
                g = metrics(a, b, edus)
                if g is None:
                    continue
                rec = per.setdefault(tech, {"gold": [], "chance": [], "len": []})
                rec["gold"].append(g)
                rec["len"].append(b - a)
                line = next(((s, e) for s, e in lines if s <= a < e), None)
                if line and line[1] - line[0] > (b - a):
                    s0 = rng.randrange(line[0], line[1] - (b - a) + 1)
                    c = metrics(s0, s0 + (b - a), edus)
                    if c is not None:
                        rec["chance"].append(c)

    def summ(xs):
        if not xs:
            return None
        return {"cover_iou": st.mean(x[0] for x in xs),
                "start_edu": st.mean(float(x[1]) for x in xs),
                "end_edu": st.mean(float(x[2]) for x in xs),
                "both": st.mean(float(x[1] and x[2]) for x in xs)}

    table = {t: {"n": len(v["gold"]), "median_chars": st.median(v["len"]),
                 "gold": summ(v["gold"]), "chance": summ(v["chance"])}
             for t, v in sorted(per.items(), key=lambda kv: -len(kv[1]["gold"]))}
    allg = [x for v in per.values() for x in v["gold"]]
    allc = [x for v in per.values() for x in v["chance"]]
    out = {"articles_used": n_articles, "articles_fallback_excluded": n_fallback,
           "tolerance_chars": TOL, "all": {"n": len(allg), "gold": summ(allg),
                                            "chance": summ(allc)},
           "per_technique": table}
    (ROOT / "results" / "discourse_alignment.json").write_text(json.dumps(out, indent=2))
    print(f"articles used {n_articles}, fallback excluded {n_fallback}")
    hdr = f"{'technique':34s} {'n':>5s} {'chars':>5s} | {'IoU':>5s} {'both':>5s} | {'IoU*':>5s} {'both*':>5s}"
    print(hdr + "   (* = chance control)")
    for t, v in [("ALL", {"n": len(allg), "median_chars": 0, **out["all"]})] + list(table.items()):
        g, c = v["gold"], v["chance"] or {"cover_iou": float("nan"), "both": float("nan")}
        print(f"{t:34s} {v['n']:5d} {v['median_chars']:5.0f} | {g['cover_iou']:5.3f} {g['both']:5.3f}"
              f" | {c['cover_iou']:5.3f} {c['both']:5.3f}")


if __name__ == "__main__":
    main()
