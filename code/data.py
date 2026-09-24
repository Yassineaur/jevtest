"""Data pipeline for jevpersuation: records -> CEM views -> token tensors.

Inputs are the project-local span files built by `code/build_span_jsonl.py` with
`--keep-empty-paragraphs` (the shared `train_subtask3_spans.jsonl` drops every paragraph without a
technique, which would leave the model with no negative paragraphs):

  data/train_spans_all.jsonl   9,498 paragraphs, 3,760 with a technique, 446 articles
  data/dev_spans_all.jsonl     3,127 paragraphs, 1,120 with a technique,  90 articles

Splits: train is cut BY ARTICLE into fit (90%) and holdout (10%). Holdout is for early stopping,
thresholds and temperature; dev is touched only for the reported numbers.

Evidence supervision follows augment.py (MVP v1): the evidence head is supervised on
evidence_present views (V0, V2); every view supervises the label head. Within an
evidence_present view a technique's evidence location is "known" when its label is 0 (no span
anywhere) or when at least one of its gold spans was located in the text; a positive technique
with no located span is masked out of the evidence losses.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import torch

import augment as A

ROOT = Path(__file__).resolve().parents[1]
TRAIN_ALL = ROOT / "data" / "train_spans_all.jsonl"
DEV_ALL = ROOT / "data" / "dev_spans_all.jsonl"
T = len(A.ENGLISH_19)

# Some gold text carries zero-width characters; strip them BEFORE any offset is computed so the
# paragraph, the span texts and the tokenizer all agree.
_ZW = dict.fromkeys(map(ord, "​‌‍⁠﻿"), None)
CF_VIEWS = ("V1", "V3", "V4")


def clean(s: str) -> str:
    return s.translate(_ZW)


def load(path: Path) -> List[dict]:
    recs = A.load_records(path)
    for r in recs:
        r["paragraph_text"] = clean(r["paragraph_text"])
        for sp in r.get("spans", []):
            sp["text"] = clean(sp["text"])
    return recs


def split_by_article(recs: List[dict], holdout_frac: float = 0.1,
                     seed: int = 0) -> Tuple[List[dict], List[dict]]:
    arts = sorted({r["article_id"] for r in recs})
    random.Random(seed).shuffle(arts)
    hold = set(arts[:max(1, int(round(holdout_frac * len(arts))))])
    return ([r for r in recs if r["article_id"] not in hold],
            [r for r in recs if r["article_id"] in hold])


def plain_views(recs: List[dict]) -> List[dict]:
    """V0 only (no augmentation): the evaluation view and the no-CEM ablation."""
    out = []
    for r in recs:
        out.append({"view": "V0", "id": r["id"], "text": r["paragraph_text"],
                    "label": A.label_vector(r.get("paragraph_techniques", [])),
                    "spans": A.base_spans(r), "evidence_present": True})
    return out


def epoch_views(recs: List[dict], pool: Dict[str, List[str]], rng: random.Random,
                use_cem: bool = True, max_cf_per_record: int = 3,
                inject_per_tech: int = 100) -> List[dict]:
    """One epoch of training views, freshly sampled each epoch.

    Every record contributes V0. With CEM on, it also contributes V2 and up to
    `max_cf_per_record` of its V1/V3/V4 views, and each technique gets `inject_per_tech` V6
    views built from paragraphs that lack it.
    """
    if not use_cem:
        return plain_views(recs)
    out: List[dict] = []
    for r in recs:
        vs = A.make_views(r, pool, rng)
        for v in vs:
            v["id"] = r["id"]
        out += [v for v in vs if v["view"] in ("V0", "V2")]
        cf = [v for v in vs if v["view"] in CF_VIEWS]
        rng.shuffle(cf)
        out += cf[:max_cf_per_record]
    inj = A.inject_views(recs, pool, rng, max_per_tech=inject_per_tech)
    for v in inj:
        v["id"] = "inject"
    out += inj
    rng.shuffle(out)
    return out


CEM_V2_POOL = ROOT / "data" / "cem_v2_pool.jsonl"


def load_cem_v2_pool(path: Path = CEM_V2_POOL) -> Dict[str, List[dict]]:
    """Frozen v2 pool grouped by pair id (each pair = evidence edit + matched control)."""
    pairs: Dict[str, List[dict]] = {}
    for line in path.open(encoding="utf-8"):
        if line.strip():
            v = json.loads(line)
            v["id"] = v["orig_id"]
            pairs.setdefault(v["pair"], []).append(v)
    pairs = {k: vs for k, vs in pairs.items() if len(vs) == 2}
    fill_tech2(pairs.values())
    return pairs


def fill_tech2(pair_lists) -> None:
    """SWAP views built before tech2 was recorded: recover it exactly as the technique the SWAP
    label switches on that its matched control (which keeps the original labels) does not."""
    for vs in pair_lists:
        ev = next((v for v in vs if v["view"] == "SWAP"), None)
        ct = next((v for v in vs if v["view"] == "SWAP_C"), None)
        if ev is not None and ct is not None and not ev.get("tech2"):
            new = [A.ENGLISH_19[i] for i, (a, b) in enumerate(zip(ev["label"], ct["label"]))
                   if a > 0.5 and b < 0.5]
            if len(new) == 1:
                ev["tech2"] = new[0]


def epoch_views_v2(recs: List[dict], pairs: Dict[str, List[dict]], rng: random.Random,
                   pairs_per_epoch: int = 6000, soft: Dict[str, float] | None = None) -> List[dict]:
    """All original (V0) paragraphs plus `pairs_per_epoch` whole pairs sampled from the frozen
    CEM v2 pool. `soft` maps a family (e.g. "INJECT") to its audited validity: the edited
    technique's target becomes that probability instead of 0/1 (label-noise-aware target)."""
    out = plain_views(recs)
    keys = sorted(pairs)
    for k in rng.sample(keys, min(pairs_per_epoch, len(keys))):
        for v in pairs[k]:
            v = dict(v)
            if soft and v["view"] in soft:
                lab = list(v["label"])
                q = soft[v["view"]]
                t = A.LAB2ID[v["tech"]]
                lab[t] = q if lab[t] > 0.5 else 1.0 - q
                if v.get("tech2"):
                    t2 = A.LAB2ID[v["tech2"]]
                    lab[t2] = q if lab[t2] > 0.5 else 1.0 - q
                v["label"] = lab
            out.append(v)
    rng.shuffle(out)
    return out


def char_to_token_span(offsets: Sequence[Tuple[int, int]], a: int, b: int):
    """Token span [i, j) of the tokens overlapping chars [a, b); None if none survive truncation.

    DeBERTa's offsets for a word-initial piece can include the preceding space, so a token
    counts as inside when it overlaps the span on at least one non-space character; callers
    pass offsets already trimmed of leading spaces by `encode`.
    """
    idx = [k for k, (s, e) in enumerate(offsets) if e > s and e > a and s < b]
    if not idx:
        return None
    return idx[0], idx[-1] + 1


def edu_targets(offs, segs):
    """Per-token silver EDU start/end targets (L, 2) from paragraph-relative char EDUs."""
    tgt = torch.zeros(len(offs), 2)
    for s, e in segs:
        ts = char_to_token_span(offs, s, e)
        if ts is not None:
            tgt[ts[0], 0] = 1.0
            tgt[ts[1] - 1, 1] = 1.0
    return tgt


def encode(views: List[dict], tokenizer, max_len: int = 512,
           edus: Dict[str, list] | None = None) -> List[dict]:
    """Tokenize views and map gold char spans to token spans.

    With `edus` (from edus.load), original (V0) views of parsed paragraphs also get silver
    EDU start/end targets for the segmenter head; other views have no target (the edit moved or
    removed text the parser never saw)."""
    feats = []
    for v in views:
        text = v["text"]
        enc = tokenizer(text, truncation=True, max_length=max_len, return_offsets_mapping=True)
        offs = []
        for s, e in enc["offset_mapping"]:
            while s < e and text[s].isspace():  # trim the leading space DeBERTa folds in
                s += 1
            offs.append((s, e))
        label = torch.tensor(v["label"], dtype=torch.float32)
        spans: List[Tuple[int, int, int]] = []
        src: List[int] = []  # index into v["spans"] of each kept span (for audits)
        known = torch.zeros(T, dtype=torch.bool)
        ev = bool(v.get("evidence_present"))
        if ev:
            located = set()
            last_char = max((e for s, e in offs if e > s), default=0)
            for k, sp in enumerate(v.get("spans", [])):
                if sp["tech"] not in A.LAB2ID:
                    continue
                if sp["end"] > last_char:  # cut by truncation: location unknown, not partial
                    continue
                ts = char_to_token_span(offs, sp["start"], sp["end"])
                if ts is None:
                    continue
                t = A.LAB2ID[sp["tech"]]
                spans.append((t, ts[0], ts[1]))
                src.append(k)
                located.add(t)
            for t in range(T):
                known[t] = (label[t] < 0.5) or (t in located)
        segs = edus.get(v.get("id", "")) if (edus and v["view"] == "V0") else None
        seg = edu_targets(offs, segs) if segs else None
        feats.append({"input_ids": enc["input_ids"], "label": label, "spans": spans, "src": src,
                      "seg": seg,
                      "known": known, "ev": ev, "view": v["view"], "id": v.get("id", ""),
                      "text": text, "offsets": offs})
    return feats


def collate(batch: List[dict], pad_id: int = 0) -> dict:
    L = max(len(f["input_ids"]) for f in batch)
    B = len(batch)
    ids = torch.full((B, L), pad_id, dtype=torch.long)
    mask = torch.zeros((B, L), dtype=torch.long)
    S = max(1, max(len(f["spans"]) for f in batch))
    gold = torch.full((B, S, 3), -1, dtype=torch.long)  # (technique, i, j)
    seg = torch.zeros((B, L, 2))
    seg_mask = torch.zeros((B, L), dtype=torch.bool)
    for b, f in enumerate(batch):
        n = len(f["input_ids"])
        ids[b, :n] = torch.tensor(f["input_ids"])
        mask[b, :n] = 1
        for k, sp in enumerate(f["spans"]):
            gold[b, k] = torch.tensor(sp)
        if f.get("seg") is not None:
            seg[b, :n] = f["seg"]
            seg_mask[b, 1:n - 1] = True  # content tokens only
    return {
        "input_ids": ids, "attention_mask": mask, "gold": gold, "seg": seg, "seg_mask": seg_mask,
        "label": torch.stack([f["label"] for f in batch]),
        "known": torch.stack([f["known"] for f in batch]),
        "ev": torch.tensor([f["ev"] for f in batch], dtype=torch.bool),
        "view": [f["view"] for f in batch],
    }


def batches(feats: List[dict], batch_size: int, rng: random.Random | None = None,
            pad_id: int = 0):
    """Length-bucketed batches (sort by length inside shuffled chunks) to cut padding."""
    order = list(range(len(feats)))
    if rng is not None:
        rng.shuffle(order)
    chunk = batch_size * 50
    groups = []
    for c in range(0, len(order), chunk):
        part = sorted(order[c:c + chunk], key=lambda k: len(feats[k]["input_ids"]))
        groups += [part[i:i + batch_size] for i in range(0, len(part), batch_size)]
    if rng is not None:
        rng.shuffle(groups)
    for g in groups:
        yield collate([feats[k] for k in g], pad_id)


def main() -> None:
    """CPU self-check: every located gold span must decode back to its text."""
    import sys
    from transformers import AutoTokenizer
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    tok = AutoTokenizer.from_pretrained("microsoft/deberta-v3-base")
    for path in (TRAIN_ALL, DEV_ALL):
        recs = load(path)
        views = plain_views(recs)
        feats = encode(views, tok)
        n_sp = n_bad = n_unknown = n_slack = 0
        for v, f in zip(views, feats):
            for k, (t, i, j) in zip(f["src"], f["spans"]):
                sp = v["spans"][k]
                n_sp += 1
                a, b = f["offsets"][i][0], f["offsets"][j - 1][1]
                surface = f["text"][a:b]
                # the token cover must contain the gold text; it may only widen it to
                # whole-token boundaries
                if sp["text"].strip().lower() not in surface.lower():
                    n_bad += 1
                n_slack += len(surface) - len(sp["text"].strip())
            n_unknown += int((~f["known"]).sum())
        print(f"  mean extra chars from token rounding: {n_slack / max(1, n_sp):.2f}")
        fit, hold = split_by_article(recs)
        print(f"{path.name}: paragraphs={len(recs)} spans_mapped={n_sp} cover_mismatch={n_bad} "
              f"unknown_tech_slots={n_unknown} fit/holdout={len(fit)}/{len(hold)}")
    recs = load(TRAIN_ALL)
    fit, _ = split_by_article(recs)
    pool = A.build_pool(fit)
    views = epoch_views(fit, pool, random.Random(0))
    from collections import Counter
    print("one CEM epoch:", dict(Counter(v["view"] for v in views)), "total", len(views))


if __name__ == "__main__":
    main()
