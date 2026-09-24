"""Counterfactual Evidence Manipulation (CEM) augmentation for jevpersuation.

Turns the SemEval-2023 Task 3 span gold (paragraph + per-technique evidence spans) into
perturbed views with well-defined 19-dim label targets, so a model is trained to make its
technique labels a faithful function of the evidence spans rather than paragraph priors.

This is the "faithfulness engine" of the training recipe. It is pure data manipulation
(no torch), so it is cheap to run and test on CPU. The swap/inject views reuse REAL gold
spans, so the augmentation is auditable (no LLM generation except the deferred V5 paraphrase).

Two supervision channels come out of each view:
  - The LABEL head is supervised on EVERY view (V0-V6) with the view's 19-dim label target.
  - The EVIDENCE head is supervised only where all original gold spans are intact at
    unchanged char offsets (the "evidence_present" views: V0 original and V2 distractor).
    The evidence-manipulated views (V1 kill, V3 swap, V4 relocate, V6 inject) carry
    "evidence_present": False and train the LABEL head only (MVP v1). This keeps the offset
    bookkeeping exact; per-view evidence supervision is a v2 refinement.

Views (per (paragraph, technique t, gold evidence span s)); label target is the original
19-dim vector except for the technique(s) the view manipulates:
  V0 original      : unchanged.                     target t = 1 (anchor)   [evidence_present]
  V1 evidence kill : erase s.                       target t = 1 iff another t span remains
  V2 distractor    : swap two words outside s.      target t = 1 (invariant) [evidence_present]
  V3 technique swap: replace s with a t' cue.       target t = 0 (if sole), t' = 1
  V4 relocation    : move s to a new position.      target t = 1 (position-invariant)
  V6 evidence inject: insert a t cue into a t-NEG paragraph. target t = 1
  (V5 paraphrase is deferred: it needs text generation and must be audited vs gold.)

Read-only input: the merged span jsonl under ../semeval/data/en/. Nothing is written outside
this project folder.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ENGLISH_19 = sorted([
    "Appeal_to_Authority", "Appeal_to_Fear-Prejudice", "Appeal_to_Hypocrisy",
    "Appeal_to_Popularity", "Causal_Oversimplification", "Conversation_Killer", "Doubt",
    "Exaggeration-Minimisation", "False_Dilemma-No_Choice", "Flag_Waving",
    "Guilt_by_Association", "Loaded_Language", "Name_Calling-Labeling",
    "Obfuscation-Vagueness-Confusion", "Red_Herring", "Repetition", "Slogans", "Straw_Man",
    "Whataboutism",
])
LAB2ID = {l: i for i, l in enumerate(ENGLISH_19)}

DEFAULT_TRAIN = (
    Path(__file__).resolve().parents[2] / "semeval" / "data" / "en" / "train_subtask3_spans.jsonl"
)


def load_records(path: Path) -> List[dict]:
    recs: List[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    return recs


def find_span(text: str, span: str) -> int:
    i = text.find(span)
    return i if i >= 0 else text.lower().find(span.lower())


def label_vector(techs: List[str]) -> List[float]:
    v = [0.0] * len(ENGLISH_19)
    for t in techs:
        if t in LAB2ID:
            v[LAB2ID[t]] = 1.0
    return v


def _set(vec: List[float], tech: str, val: float) -> List[float]:
    out = vec[:]
    if tech in LAB2ID:
        out[LAB2ID[tech]] = val
    return out


def build_pool(recs: List[dict]) -> Dict[str, List[str]]:
    """technique -> list of gold span texts, for the swap/inject views."""
    pool: Dict[str, List[str]] = {t: [] for t in ENGLISH_19}
    for r in recs:
        for sp in r.get("spans", []):
            t = sp.get("technique", "")
            s = sp.get("text", "").strip()
            if t in pool and s:
                pool[t].append(s)
    return pool


def base_spans(rec: dict) -> List[dict]:
    """Gold evidence spans as {tech, text, start, end} with char offsets into the paragraph.

    Only spans actually located inside the paragraph text are returned (cross-line or
    mismatched spans are skipped). Offsets are exact, so they are valid for the V0 text and,
    because V2 only swaps two non-span words of equal total length, for the V2 text too.
    """
    para = rec["paragraph_text"]
    out: List[dict] = []
    for sp in rec.get("spans", []):
        t, s = sp.get("technique", ""), sp.get("text", "")
        i = find_span(para, s)
        if i >= 0:
            out.append({"tech": t, "text": s, "start": i, "end": i + len(s)})
    return out


def relocate_spans(text: str, spans: List[dict]) -> List[dict]:
    """Re-locate each span (by its text) in a modified text and verify the slice.

    The span TEXT is unchanged under the V2 word-swap, so find_span recovers its new offset
    even when the between-region shifted. Any span that no longer matches is dropped.
    """
    out: List[dict] = []
    for sp in spans:
        i = find_span(text, sp["text"])
        if i < 0:
            continue
        b = i + len(sp["text"])
        if text[i:b].lower() != sp["text"].lower():
            continue
        out.append({"tech": sp["tech"], "text": sp["text"], "start": i, "end": b})
    return out


def found_spans(rec: dict) -> Dict[str, List[Tuple[str, int, int]]]:
    """technique -> list of (span_text, start, end) actually located inside the paragraph."""
    para = rec["paragraph_text"]
    out: Dict[str, List[Tuple[str, int, int]]] = {}
    for sp in rec.get("spans", []):
        t, s = sp.get("technique", ""), sp.get("text", "")
        i = find_span(para, s)
        if i >= 0:
            out.setdefault(t, []).append((s, i, i + len(s)))
    return out


def make_views(rec: dict, pool: Dict[str, List[str]], rng: random.Random) -> List[dict]:
    para = rec["paragraph_text"]
    base = label_vector(rec.get("paragraph_techniques", []))
    bspans = base_spans(rec)
    views: List[dict] = [{
        "view": "V0", "text": para, "label": base[:], "spans": bspans,
        "evidence_present": True, "why": "original (anchor)",
    }]
    # V2 distractor (once): swap two words that do not overlap ANY gold span, so every
    # span's char offset is unchanged in the view text.
    intervals = [(sp["start"], sp["end"]) for sp in bspans]

    def overlaps_span(tk) -> bool:
        return any(not (tk.end() <= a or tk.start() >= b) for a, b in intervals)

    toks = [tk for tk in re.finditer(r"\S+", para) if not overlaps_span(tk)]
    if len(toks) >= 2:
        a, b = rng.sample(toks, 2)
        x, y = (a, b) if a.start() < b.start() else (b, a)
        txt = (para[:x.start()] + y.group() + para[x.end():y.start()]
               + x.group() + para[y.end():])
        # The swap shifts any span that sits between the two words, so re-locate every span
        # by its (unchanged) text. Only keep the view for evidence supervision if the full
        # span set survived the relocation.
        spans2 = relocate_spans(txt, bspans)
        views.append({"view": "V2", "text": txt, "label": base[:], "spans": spans2,
                      "evidence_present": len(spans2) == len(bspans) > 0,
                      "why": "swap two non-evidence words; label must stay"})
    # Per-technique evidence-manipulated views (label head only in MVP v1).
    for t, spans in found_spans(rec).items():
        s, i, j = spans[0]
        n_t = len(spans)
        drop_t = 1.0 if n_t - 1 > 0 else 0.0
        # V1 evidence kill
        views.append({
            "view": "V1", "text": (para[:i] + " " + para[j:]).strip(),
            "label": _set(base, t, drop_t), "tech": t, "evidence_present": False,
            "why": "erase evidence span; label drops only if it was the sole span",
        })
        # V3 technique swap
        cand = [tt for tt in pool if tt != t and pool[tt]]
        if cand:
            tp = rng.choice(cand)
            cue = rng.choice(pool[tp])
            views.append({
                "view": "V3", "text": para[:i] + " " + cue + " " + para[j:],
                "label": _set(_set(base, t, drop_t), tp, 1.0),
                "tech": t, "tech2": tp, "evidence_present": False,
                "why": f"replace {t} evidence with a {tp} cue; label must move to {tp}",
            })
        # V4 relocation
        parts = (para[:i] + " " + para[j:]).strip().split(" ")
        if parts:
            parts.insert(rng.randrange(len(parts)), s)
            views.append({"view": "V4", "text": " ".join(parts), "label": base[:], "tech": t,
                          "evidence_present": False,
                          "why": "move the evidence span to a new position; label must stay"})
    return views


def inject_views(recs: List[dict], pool: Dict[str, List[str]], rng: random.Random,
                 max_per_tech: int = 2) -> List[dict]:
    """V6: insert a t cue into a t-negative paragraph. target t = 1. Label head only."""
    neg: Dict[str, List[dict]] = {}
    for r in recs:
        present = set(r.get("paragraph_techniques", []))
        for t in ENGLISH_19:
            if t not in present:
                neg.setdefault(t, []).append(r)
    out: List[dict] = []
    for t in ENGLISH_19:
        if not pool.get(t) or not neg.get(t):
            continue
        for _ in range(max_per_tech):
            r = rng.choice(neg[t])
            para = r["paragraph_text"]
            toks = list(re.finditer(r"\S+", para))
            if not toks:
                continue
            tok = rng.choice(toks)
            cue = rng.choice(pool[t])
            out.append({
                "view": "V6",
                "text": para[:tok.end()] + " " + cue + " " + para[tok.end():],
                "label": _set(label_vector(r.get("paragraph_techniques", [])), t, 1.0),
                "tech": t, "evidence_present": False,
                "why": f"inject a {t} cue into a {t}-negative paragraph; label must appear",
            })
    return out


def validate(views: List[dict]) -> int:
    """Check every evidence_present view's span offsets are valid and self-consistent.

    Returns the number of span offsets that failed the check.
    """
    bad = 0
    for v in views:
        if not v.get("evidence_present"):
            continue
        text = v["text"]
        for sp in v.get("spans", []):
            a, b, s = sp["start"], sp["end"], sp["text"]
            if not (0 <= a < b <= len(text)):
                bad += 1
                continue
            if text[a:b] != s:
                # allow case-only mismatch (find_span falls back to a case-insensitive match)
                if text[a:b].lower() != s.lower():
                    bad += 1
    return bad


def techs_of(vec: List[float]) -> List[str]:
    return [ENGLISH_19[i] for i, l in enumerate(vec) if l > 0.5]


def main() -> None:
    ap = argparse.ArgumentParser(description="CEM augmentation smoke test.")
    ap.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    ap.add_argument("--n-records", type=int, default=2)
    ap.add_argument("--n-inject", type=int, default=4)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--validate-all", action="store_true",
                    help="generate and validate views for the whole train split")
    a = ap.parse_args()
    try:  # the console is cp1252; some gold text has zero-width spaces
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    rng = random.Random(a.seed)
    recs = load_records(a.train)
    pool = build_pool(recs)
    print(f"loaded {len(recs)} records from {a.train}")

    if a.validate_all:
        total_views = 0
        total_bad = 0
        present = 0
        for r in recs:
            vs = make_views(r, pool, rng) + inject_views([r], pool, rng, max_per_tech=1)
            total_views += len(vs)
            total_bad += validate(vs)
            present += sum(1 for v in vs if v.get("evidence_present"))
        print(f"views generated={total_views}  evidence_present={present}  bad_offsets={total_bad}")
        return

    sizes = {t: len(pool[t]) for t in ENGLISH_19 if pool[t]}
    print("span pool per technique:", sizes)
    for r in recs[:a.n_records]:
        print("=" * 72)
        print("PARA:", r["paragraph_text"][:200])
        print("GOLD TECHS:", r.get("paragraph_techniques", []))
        views = make_views(r, pool, rng)
        print(f"  offset self-check: bad={validate(views)}")
        for v in views:
            nsp = len(v.get("spans", [])) if v.get("evidence_present") else 0
            print(f"  [{v['view']}] label={techs_of(v['label'])} spans={nsp}")
            print(f"      {v.get('why', '')}")
            print(f"      {v['text'][:170]}")
    print("=" * 72)
    print("V6 inject examples:")
    for v in inject_views(recs, pool, rng, max_per_tech=1)[:a.n_inject]:
        print(f"  [{v['view']}] {v['tech']} -> {techs_of(v['label'])}")
        print(f"      {v['text'][:170]}")


if __name__ == "__main__":
    main()
