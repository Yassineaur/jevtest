"""CEM v2: artifact-balanced counterfactual evidence views (design: notes/cem_v2_design.md).

Every view is ONE exact splice of the original paragraph (replace chars [a, b) by `ins`), so the
char offsets of every surviving gold span, and of any inserted span, are known exactly. Each
evidence edit comes with a matched CONTROL edit of the same kind and shape on non-evidence text
with the labels unchanged, so "the text was edited" carries no information about the label.

Edit points are sentence boundaries or DMRST EDU starts (never mid-phrase). Shape matching: if
the evidence span is a whole run of EDUs, its control is a non-evidence EDU; otherwise a
non-evidence word window of about the same length.

Families
  train: KILL / KILL_C, INJECT / INJECT_C, SWAP / SWAP_C
  eval only (held out from training): RELOC / RELOC_C, SUFF / SUFF_C
View dict: view, pair (id shared by an edit and its control), text, label (19 floats),
spans [{tech, text, start, end}] (all gold evidence in the edited text), evidence_present,
tech (edited technique), orig_id, orig_text (for the fluency filter), why.
Pure Python; reads nothing outside this project except via data/edus loaders.
"""
from __future__ import annotations

import random
import re
from typing import Dict, List, Optional, Sequence, Tuple

import augment as A

TOL = 2
TRAIN_FAMILIES = ("KILL", "INJECT", "SWAP")
# techniques that cannot be CREATED by inserting one span: Repetition requires the phrase to
# recur in the text, so a single inserted occurrence is not Repetition (definitional exclusion)
NO_INSERT = {"Repetition"}
EVAL_FAMILIES = ("RELOC", "SUFF")
_SENT = re.compile(r"[.!?][\"'”’)]*\s+(?=\S)")  # end of a sentence


# ------------------------------------------------------------------------------ primitives
def boundaries(text: str, segs: Optional[Sequence[Tuple[int, int]]], spans: List[dict]) -> List[int]:
    """Char positions where a unit may be inserted: paragraph start, sentence starts, EDU
    starts, paragraph end; never inside a gold span."""
    pts = {0, len(text)}
    pts.update(m.end() for m in _SENT.finditer(text))
    for s, _ in segs or []:
        if 0 < s < len(text) and (text[s - 1].isspace()):
            pts.add(s)
    occ = [(sp["start"], sp["end"]) for sp in spans]
    return sorted(p for p in pts if all(not (a < p < b) for a, b in occ))


def splice(text: str, a: int, b: int, ins: str) -> Tuple[str, callable]:
    """Replace text[a:b] by ins with clean spacing. Returns (new_text, mapper) where mapper(pos)
    maps an original offset outside [a, b) to the new text (None if it was inside)."""
    # swallow one adjacent space on deletion so no double space or ' ,' is left
    if not ins:
        if b < len(text) and text[b] == " ":
            b += 1
        elif a > 0 and text[a - 1] == " ":
            a -= 1
    else:
        ins = ins.strip()
        left = a > 0 and text[a - 1].isalnum()
        right = b < len(text) and text[b].isalnum()
        if a == b:  # pure insertion at a boundary (a word start or the end)
            ins = (" " + ins) if a == len(text) else (ins + " ")
            if a == len(text) and a > 0 and text[a - 1].isspace():
                ins = ins.lstrip()
        else:
            ins = (" " if left else "") + ins + (" " if right else "")
    new = text[:a] + ins + text[b:]
    shift = len(ins) - (b - a)

    def mapper(pos: int, is_end: bool = False):
        if pos < a or (is_end and pos <= a):
            return pos
        if pos >= b or (not is_end and pos >= b):
            return pos + shift
        return None
    return new, mapper


def carry_spans(spans: List[dict], mapper, drop: Optional[dict] = None) -> List[dict]:
    out = []
    for sp in spans:
        if drop is not None and sp is drop:
            continue
        s, e = mapper(sp["start"]), mapper(sp["end"], True)
        if s is None or e is None or e <= s:
            return None  # an edit cut through another gold span: unusable for evidence
        out.append({"tech": sp["tech"], "text": sp["text"], "start": s, "end": e})
    return out


def is_edu_aligned(a: int, b: int, segs) -> bool:
    if not segs:
        return False
    return (min(abs(a - s) for s, _ in segs) <= TOL) and (min(abs(b - e) for _, e in segs) <= TOL)


def nonevidence_chunk(text: str, spans: List[dict], segs, n_chars: int, edu_shape: bool,
                      rng: random.Random, avoid: Tuple[int, int] = (-1, -1)):
    """(start, end) of a non-evidence region shaped like the evidence: a whole EDU when
    edu_shape, else a word window of about n_chars. None if the paragraph has none."""
    occ = [(sp["start"], sp["end"]) for sp in spans] + [avoid]
    free = lambda s, e: all(e <= a or s >= b for a, b in occ)  # noqa: E731
    if edu_shape and segs:
        cands = [(s, e) for s, e in segs if free(s, e) and 0.5 * n_chars <= e - s <= 2 * n_chars]
        if cands:
            return rng.choice(cands)
        return None
    starts = [0] + [m.end() for m in re.finditer(r"\s+", text)]
    rng.shuffle(starts)
    for s in starts[:40]:
        e = text.find(" ", s + max(1, int(0.8 * n_chars)))
        e = len(text) if e < 0 else e
        while e > s and text[e - 1] in ",;:":
            e -= 1
        if e > s and e - s <= 1.3 * n_chars + 4 and free(s, e):
            return (s, e)
    return None


def foreign_chunk(recs: List[dict], exclude_id: str, n_chars: int, edu_shape: bool,
                  edus: Dict[str, list], rng: random.Random):
    """Non-evidence text of about n_chars from another paragraph (shape-matched)."""
    for _ in range(60):
        r = rng.choice(recs)
        if r["id"] == exclude_id or len(r["paragraph_text"]) < n_chars + 2:
            continue
        c = nonevidence_chunk(r["paragraph_text"], gold_spans(r), edus.get(r["id"]), n_chars,
                              edu_shape, rng)
        if c:
            return r["paragraph_text"][c[0]:c[1]]
    return None


def _view(view, pair, text, label, spans, tech, rec, why):
    return {"view": view, "pair": pair, "text": text, "label": label, "spans": spans or [],
            "evidence_present": spans is not None, "tech": tech, "orig_id": rec["id"],
            "orig_text": rec["paragraph_text"], "why": why}


def gold_spans(rec: dict) -> List[dict]:
    """Located gold spans with offsets and text trimmed to non-space characters."""
    text = rec["paragraph_text"]
    out = []
    for sp in A.base_spans(rec):
        a, b = sp["start"], sp["end"]
        while a < b and text[a].isspace():
            a += 1
        while b > a and text[b - 1].isspace():
            b -= 1
        if b > a:
            out.append({"tech": sp["tech"], "text": text[a:b], "start": a, "end": b})
    return out


def isolated(spans: List[dict]) -> List[dict]:
    """Spans that overlap no other gold span (an edit must touch exactly one gold span)."""
    return [s for s in spans if all(o is s or o["end"] <= s["start"] or o["start"] >= s["end"]
                                    for o in spans)]


# ------------------------------------------------------------------------------- families
def family_views(rec: dict, family: str, pool: Dict[str, List[str]], recs: List[dict],
                 edus: Dict[str, list], rng: random.Random, pair_id: str) -> List[dict]:
    """Views for one family on one paragraph: [evidence edit, matched control] or []."""
    text = rec["paragraph_text"]
    spans = gold_spans(rec)
    segs = edus.get(rec["id"])
    base = A.label_vector(rec.get("paragraph_techniques", []))
    by_t: Dict[str, List[dict]] = {}
    for sp in spans:
        by_t.setdefault(sp["tech"], []).append(sp)
    iso = {id(x) for x in isolated(spans)}
    single = [ss[0] for t, ss in by_t.items()
              if len(ss) == 1 and t in A.LAB2ID and id(ss[0]) in iso]

    if family == "INJECT":
        absent = [t for t in A.ENGLISH_19
                  if base[A.LAB2ID[t]] < 0.5 and pool.get(t) and t not in NO_INSERT]
        pts = boundaries(text, segs, spans)
        if not absent or not pts:
            return []
        t = rng.choice(absent)
        cue = rng.choice(pool[t])
        p = rng.choice(pts)
        new, mp = splice(text, p, p, cue)
        cs = new.find(cue.strip(), max(0, p - 1))
        kept = carry_spans(spans, mp)
        ev = None if kept is None else kept + [{"tech": t, "text": cue.strip(), "start": cs,
                                                "end": cs + len(cue.strip())}]
        edu_shape = len(cue) > 40
        chunk = foreign_chunk(recs, rec["id"], len(cue), edu_shape, edus, rng)
        if chunk is None:
            return []
        newc, mpc = splice(text, p, p, chunk)
        return [_view("INJECT", pair_id, new, A._set(base, t, 1.0), ev, t, rec,
                      f"insert a real {t} span at a boundary; {t} must appear"),
                _view("INJECT_C", pair_id, newc, base[:], carry_spans(spans, mpc), t, rec,
                      "insert same-shape non-evidence text at the same boundary; labels unchanged")]

    if not single:
        return []
    s = rng.choice(single)
    t = s["tech"]
    a, b = s["start"], s["end"]
    edu_shape = is_edu_aligned(a, b, segs)
    ctrl = nonevidence_chunk(text, spans, segs, b - a, edu_shape, rng)
    if ctrl is None:
        return []
    ca, cb = ctrl

    if family == "KILL":
        new, mp = splice(text, a, b, "")
        newc, mpc = splice(text, ca, cb, "")
        return [_view("KILL", pair_id, new, A._set(base, t, 0.0), carry_spans(spans, mp, drop=s),
                      t, rec, f"delete the only {t} span; {t} must disappear"),
                _view("KILL_C", pair_id, newc, base[:], carry_spans(spans, mpc), t, rec,
                      "delete same-shape non-evidence text; labels unchanged")]

    if family == "SWAP":
        cand = [tt for tt in A.ENGLISH_19 if tt != t and pool.get(tt) and base[A.LAB2ID[tt]] < 0.5
                and tt not in NO_INSERT]
        if not cand:
            return []
        t2 = rng.choice(cand)
        cue = rng.choice(pool[t2]).strip()
        new, mp = splice(text, a, b, cue)
        cs = new.find(cue, max(0, a - 1))
        kept = carry_spans(spans, mp, drop=s)
        ev = None if kept is None else kept + [{"tech": t2, "text": cue, "start": cs,
                                                "end": cs + len(cue)}]
        filler = foreign_chunk(recs, rec["id"], len(cue), len(cue) > 40, edus, rng)
        if filler is None:
            return []
        newc, mpc = splice(text, ca, cb, filler)
        lab = A._set(A._set(base, t, 0.0), t2, 1.0)
        sw = _view("SWAP", pair_id, new, lab, ev, t, rec,
                   f"replace the only {t} span by a real {t2} span; {t} off, {t2} on")
        sw["tech2"] = t2
        return [sw,
                _view("SWAP_C", pair_id, newc, base[:], carry_spans(spans, mpc), t, rec,
                      "replace same-shape non-evidence text by non-evidence text; unchanged")]

    if family == "RELOC":
        pts = [p for p in boundaries(text, segs, spans) if not (a <= p <= b)]
        if not pts:
            return []
        p = rng.choice(pts)
        cut, mp = splice(text, a, b, "")
        p2 = mp(p) if p < a or p > b else None
        if p2 is None:
            return []
        new, mp2 = splice(cut, p2, p2, s["text"])
        cpts = [q for q in pts if not (ca <= q <= cb)]
        if not cpts:
            return []
        q = rng.choice(cpts)
        cutc, mc = splice(text, ca, cb, "")
        q2 = mc(q)
        if q2 is None:
            return []
        newc, _ = splice(cutc, q2, q2, text[ca:cb])
        return [_view("RELOC", pair_id, new, base[:], None, t, rec,
                      f"move the only {t} span to another boundary; label must stay"),
                _view("RELOC_C", pair_id, newc, base[:], None, t, rec,
                      "move same-shape non-evidence text; label must stay")]

    if family == "SUFF":
        return [_view("SUFF", pair_id, text[a:b], A._set([0.0] * len(A.ENGLISH_19), t, 1.0),
                      None, t, rec, f"the {t} span alone"),
                _view("SUFF_C", pair_id, text[ca:cb], [0.0] * len(A.ENGLISH_19), None, t, rec,
                      "same-shape non-evidence text alone")]
    raise ValueError(family)


def generate(recs: List[dict], pool: Dict[str, List[str]], edus: Dict[str, list],
             families: Sequence[str], per_record: int = 1, seed: int = 0,
             source_recs: Optional[List[dict]] = None) -> List[dict]:
    """Pairs for every record and family (per_record attempts each). source_recs supplies the
    foreign chunks (defaults to recs; use the train-fit split for dev generation)."""
    rng = random.Random(seed)
    src = source_recs or recs
    out = []
    for r in recs:
        for fam in families:
            for k in range(per_record):
                out += family_views(r, fam, pool, src, edus, rng, f"{r['id']}|{fam}|{k}")
    return out


def validate(views: List[dict]) -> int:
    """Every carried or inserted span must match its text at its offsets."""
    bad = 0
    for v in views:
        for sp in v["spans"] if v["evidence_present"] else []:
            if v["text"][sp["start"]:sp["end"]] != sp["text"]:
                bad += 1
    return bad
