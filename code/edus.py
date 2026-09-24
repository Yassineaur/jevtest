"""Silver EDU boundaries per paragraph from the owner's cached DMRST parses (read-only).

The cache (../semeval/data/en/rst_cache/{split}_{article}.json) holds EDU leaves with
article-level char offsets over the exact article text. A paragraph id is the 1-based physical
line index of the article (as in build_span_jsonl.py), so each EDU is clipped to its paragraph
and shifted to paragraph-relative offsets, with whitespace trimmed at both edges.

Articles where the parser fell back (used_fallback) are marked None: no segmentation target.
Writes data/edus_{split}.json once; later calls load it.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
EN = ROOT.parent / "semeval" / "data" / "en"
ZW = set("​‌‍⁠﻿")  # same set data.clean removes


def _line_starts(text: str) -> Dict[str, Tuple[int, int]]:
    rows, cur = {}, 0
    for idx, raw in enumerate(text.splitlines(keepends=True), start=1):
        body = raw.rstrip("\r\n")
        if body.strip():
            rows[str(idx)] = (cur, cur + len(body))
        cur += len(raw)
    return rows


def build(split: str) -> Dict[str, Optional[List[Tuple[int, int]]]]:
    out: Dict[str, Optional[List[Tuple[int, int]]]] = {}
    for f in sorted((EN / "rst_cache").glob(f"{split}_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        aid, text = d["article_id"], d["text"]
        lines = _line_starts(text)
        for pid, (p0, p1) in lines.items():
            key = f"{aid}:{pid}"
            if d.get("used_fallback"):
                out[key] = None
                continue
            # data.load strips zero-width characters, so map raw offsets to cleaned offsets
            para = text[p0:p1]
            shift, removed = [], 0
            for ch in para:
                shift.append(removed)
                removed += ch in ZW
            shift.append(removed)
            segs = []
            for leaf in d["leaves"]:
                s, e = max(leaf["char_start"], p0), min(leaf["char_end"], p1)
                while s < e and (text[s].isspace() or text[s] in ZW):
                    s += 1
                while e > s and (text[e - 1].isspace() or text[e - 1] in ZW):
                    e -= 1
                if e > s:
                    segs.append((s - p0 - shift[s - p0], e - p0 - shift[e - p0]))
            out[key] = sorted(set(segs))
    return out


def load(split: str) -> Dict[str, Optional[List[Tuple[int, int]]]]:
    path = ROOT / "data" / f"edus_{split}.json"
    if not path.exists():
        path.write_text(json.dumps(build(split)))
    return {k: (None if v is None else [tuple(x) for x in v])
            for k, v in json.loads(path.read_text()).items()}


if __name__ == "__main__":
    import data as D
    for split, path in (("train", D.TRAIN_ALL), ("dev", D.DEV_ALL)):
        ed = load(split)
        recs = D.load(path)
        have = sum(1 for r in recs if ed.get(r["id"]))
        none = sum(1 for r in recs if r["id"] in ed and ed[r["id"]] is None)
        miss = sum(1 for r in recs if r["id"] not in ed)
        n_edu = sum(len(ed[r["id"]]) for r in recs if ed.get(r["id"]))
        # paragraph text must equal the cache slice for the offsets to be valid
        bad = 0
        for r in recs:
            for s, e in ed.get(r["id"]) or []:
                t = r["paragraph_text"]
                if e > len(t) or t[s].isspace() or t[e - 1].isspace():
                    bad += 1
        print(f"{split}: paragraphs={len(recs)} with_edus={have} fallback={none} missing={miss} "
              f"edus={n_edu} ({n_edu / max(1, have):.2f}/paragraph) out_of_range={bad}")
