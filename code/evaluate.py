"""Evaluation harness for jevpersuation checkpoints (T4 evidence model or T0 control).

Everything tuned (decision threshold, label temperature, evidence temperature) is fitted on the
article-level HOLDOUT cut from train; dev is only scored. Writes <out>/metrics.json plus
<out>/preds_dev.jsonl (per paragraph: probabilities and the top cited spans per technique).

Metrics
  quality     micro/macro F1 on dev, full-text mode (label head) and, for T4, span-grounded mode
              (max_s q_{t,s}); threshold from holdout.
  calibration label ECE/Brier raw and after one temperature fitted on holdout (the T1 baseline
              when run on T0); evidence ECE/Brier over the proposals, raw and temperature-scaled.
  evidence    for gold (paragraph, technique) pairs: top-1 span hit (token IoU >= 0.5 with a
              gold span), recall of gold spans by the top-3, and the grounding rate (share of
              cited spans that are exact substrings of the input; 1.0 by construction, checked).
  faithfulness (CEM on dev, both arms) the label change when the model's input is edited:
              kill        erase the sole gold span of t          -> p_t should fall
              kill_ctrl   erase a same-length non-evidence region -> p_t should not (matched control)
              distractor  swap two non-evidence words              -> p_t should not move
              relocate    move the gold span elsewhere             -> p_t should not move
              inject      add a real t span to a t-negative para   -> p_t should rise
              comprehensiveness (T4) erase the model's own top span vs a same-length random region.
  speed       batch-1 p50/p95 latency and batch-32 throughput on the GPU (after warm-up).

Run: ..\\torch_env\\Scripts\\python.exe code\\evaluate.py --ckpt results\\pilot\\T4_s0\\best.pt
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
from pathlib import Path

import numpy as np
import torch
from transformers import AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parent))
import augment as A  # noqa: E402
import augment_v2 as AV  # noqa: E402
import data as D  # noqa: E402
import edus as E  # noqa: E402
from model import BACKBONE, JevPersuader, proposal_targets  # noqa: E402

T = len(A.ENGLISH_19)
# bump when a metric definition changes; tables refuse to mix versions
EVAL_VERSION = "2026-09-24f"


# ------------------------------------------------------------------------------ inference
@torch.no_grad()
def run(model, feats, device, batch_size=32, keep_spans=False):
    """Returns logits (N,T), qmax (N,T) or None, and per-example proposal lists when asked."""
    model.eval()
    order = sorted(range(len(feats)), key=lambda k: len(feats[k]["input_ids"]))
    logits = np.zeros((len(feats), T), dtype=np.float32)
    qmax = np.zeros((len(feats), T), dtype=np.float32) if model.evidence else None
    props = [None] * len(feats)
    for s in range(0, len(order), batch_size):
        idx = order[s:s + batch_size]
        batch = D.collate([feats[k] for k in idx], getattr(model, 'pad_id', 0))
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
            out = model(batch["input_ids"].to(device), batch["attention_mask"].to(device),
                        seg_oracle=batch["seg"].to(device))
        logits[idx] = out["label_logits"].float().cpu().numpy()
        if model.evidence:
            qmax[idx] = out["qmax"].float().cpu().numpy()
            if keep_spans:
                pb = out["pb"].cpu().numpy()
                cols = [out[k].cpu().numpy() for k in ("pt", "pi", "pj")]
                ql = out["q_logit"].float().cpu().numpy()
                for r, k in enumerate(idx):
                    m = pb == r
                    props[k] = list(zip(cols[0][m], cols[1][m], cols[2][m], ql[m]))
    return logits, qmax, props


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


# -------------------------------------------------------------------------------- metrics
def f1s(p, y, th):
    pred, gold = p >= th, y > 0.5
    tp = (pred & gold).sum(0).astype(float)
    fp = (pred & ~gold).sum(0).astype(float)
    fn = (~pred & gold).sum(0).astype(float)
    micro = 2 * tp.sum() / max(1.0, 2 * tp.sum() + fp.sum() + fn.sum())
    per = 2 * tp / np.maximum(1.0, 2 * tp + fp + fn)
    present = gold.sum(0) > 0
    return float(micro), float(per[present].mean())


def selective(p, y, th):
    """Selective prediction over all (paragraph, technique) decisions: confidence = distance
    from the threshold in probability (|p - th| / max(th, 1 - th)); risk = error rate of the
    most confident fraction. Returns AURC (lower is better) and accuracy at 50% / 80% coverage."""
    p, y = p.ravel(), y.ravel()
    conf = np.abs(p - th) / max(th, 1 - th)
    err = ((p >= th) != (y > 0.5)).astype(float)
    order = np.argsort(-conf)
    cum = np.cumsum(err[order]) / np.arange(1, len(err) + 1)
    at = lambda c: float(1 - cum[max(0, int(c * len(err)) - 1)])  # noqa: E731
    return {"aurc": float(cum.mean()), "acc_at_50": at(0.5), "acc_at_80": at(0.8),
            "acc_full": float(1 - err.mean())}


def best_threshold(p, y):
    grid = np.arange(0.05, 0.96, 0.01)
    return float(grid[int(np.argmax([f1s(p, y, t)[0] for t in grid]))])


def ece(p, y, bins=15):
    p, y = p.ravel(), y.ravel()
    edges = np.linspace(0, 1, bins + 1)
    e = 0.0
    for a, b in zip(edges[:-1], edges[1:]):
        m = (p >= a) & (p < b) if b < 1 else (p >= a)
        if m.any():
            e += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(e)


def fit_temperature(z, y):
    """One temperature minimising NLL on held-out logits (grid, robust and deterministic)."""
    z, y = z.ravel(), y.ravel()
    best, best_t = 1e18, 1.0
    for t in np.exp(np.linspace(np.log(0.05), np.log(20.0), 241)):
        p = np.clip(sigmoid(z / t), 1e-7, 1 - 1e-7)
        nll = -(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()
        if nll < best:
            best, best_t = nll, float(t)
    return best_t


def calib(z, y, temp):
    p_raw, p_t = sigmoid(z), sigmoid(z / temp)
    return {"ece_raw": ece(p_raw, y), "brier_raw": float(((p_raw - y) ** 2).mean()),
            "ece_temp": ece(p_t, y), "brier_temp": float(((p_t - y) ** 2).mean()),
            "temperature": temp}


def proposal_arrays(props, feats):
    """Flatten proposals with their evidence targets (only evidence-known slots)."""
    zs, ys = [], []
    for pr, f in zip(props, feats):
        if not pr:
            continue
        gold = torch.full((1, max(1, len(f["spans"])), 3), -1, dtype=torch.long)
        for k, sp in enumerate(f["spans"]):
            gold[0, k] = torch.tensor(sp)
        pt = torch.tensor([p[0] for p in pr]); pi = torch.tensor([p[1] for p in pr])
        pj = torch.tensor([p[2] for p in pr])
        tg = proposal_targets(gold, torch.zeros_like(pt), pt, pi, pj).numpy()
        known = f["known"].numpy()[pt.numpy()]
        zs.append(np.array([p[3] for p in pr])[known]); ys.append(tg[known])
    return np.concatenate(zs), np.concatenate(ys)


def fit_platt(z, y):
    """Platt scaling sigmoid(a*z + b) by NLL on held-out data (coarse-to-fine grid)."""
    def search(a_grid, b_grid, best):
        for a in a_grid:
            for b in b_grid:
                p = np.clip(sigmoid(a * z + b), 1e-7, 1 - 1e-7)
                nll = -(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()
                if nll < best[0]:
                    best = (nll, float(a), float(b))
        return best

    best = search(np.linspace(0.05, 3, 60), np.linspace(-4, 4, 81), (1e18, 1.0, 0.0))
    _, a0, b0 = best
    best = search(np.linspace(a0 * 0.8, a0 * 1.2, 41), np.linspace(b0 - 0.2, b0 + 0.2, 41), best)
    return best[1], best[2]


def cited_arrays(props, feats, p_label, th):
    """(z, hit) for the top-1 span of every predicted technique with a known evidence location."""
    zs, hits = [], []
    for k, (pr, f) in enumerate(zip(props, feats)):
        best = {}
        for t, i, j, z in pr or []:
            if p_label[k, int(t)] >= th and (int(t) not in best or z > best[int(t)][0]):
                best[int(t)] = (float(z), int(i), int(j))
        gold_by_t = {}
        for t, i, j in f["spans"]:
            gold_by_t.setdefault(t, []).append((i, j))
        for t, (z, i, j) in best.items():
            if not bool(f["known"][t]):
                continue
            zs.append(z)
            hits.append(float(any(iou(i, j, gi, gj) >= 0.5 for gi, gj in gold_by_t.get(t, []))))
    return np.array(zs), np.array(hits)


def cited_span_calibration(hold, dev, temp):
    """Calibration of the spans a user actually sees (top-1 span per predicted technique vs
    whether it matches gold, IoU >= 0.5). Unlike the all-proposal ECE this is not dominated by
    easy negatives. Reports raw, the all-proposal temperature, and Platt scaling fitted on the
    holdout's cited spans."""
    (zh, yh), (z, y) = hold, dev
    if not len(z):
        return {}
    out = calib(z, y, temp)
    a, b = fit_platt(zh, yh)
    pp = sigmoid(a * z + b)
    out.update(n=int(len(z)), n_holdout=int(len(zh)), hit_rate=float(y.mean()),
               mean_q_raw=float(sigmoid(z).mean()), platt=[a, b],
               ece_platt=ece(pp, y), brier_platt=float(((pp - y) ** 2).mean()),
               mean_q_platt=float(pp.mean()))
    return out


def evidence_scores(props, feats, p_label, th):
    """Top-1 hit rate and top-3 gold recall on gold-positive technique slots; grounding rate."""
    hit = n_slot = rec_hit = n_gold = 0
    grounded = cited = 0
    for k, (pr, f) in enumerate(zip(props, feats)):
        by_t = {}
        for t, i, j, z in pr or []:
            by_t.setdefault(int(t), []).append((float(z), int(i), int(j)))
        for t in by_t:
            by_t[t].sort(reverse=True)
            if p_label[k, t] >= th:  # a cited span: check it is an exact substring
                z, i, j = by_t[t][0]
                a, b = f["offsets"][i][0], f["offsets"][j - 1][1]
                cited += 1
                grounded += int(f["text"][a:b] in f["text"] and b > a)
        gold_by_t = {}
        for t, i, j in f["spans"]:
            gold_by_t.setdefault(t, []).append((i, j))
        for t, gs in gold_by_t.items():
            cand = by_t.get(t, [])
            if not cand:
                continue
            n_slot += 1
            _, i, j = cand[0]
            hit += int(max(iou(i, j, gi, gj) for gi, gj in gs) >= 0.5)
            for gi, gj in gs:
                n_gold += 1
                rec_hit += int(any(iou(i2, j2, gi, gj) >= 0.5 for _, i2, j2 in cand[:3]))
    return {"top1_hit": hit / max(1, n_slot), "gold_recall_top3": rec_hit / max(1, n_gold),
            "grounding_rate": grounded / max(1, cited), "n_cited": cited, "n_gold_slots": n_slot}


def iou(i, j, gi, gj):
    inter = max(0, min(j, gj) - max(i, gi))
    return inter / max(1, (j - i) + (gj - gi) - inter)


# ---------------------------------------------------------------------------- faithfulness
def erase(text, a, b):
    return (text[:a] + " " + text[b:]).strip()


def control_region(text, a, b, spans, rng):
    """A same-length region that overlaps no gold span (None if the paragraph has no room)."""
    n = b - a
    cands = [m.start() for m in re.finditer(r"(?<=\s)\S|^\S", text)]
    rng.shuffle(cands)
    for s in cands:
        e = s + n
        if e <= len(text) and all(e <= sa or s >= sb for sa, sb in spans):
            return s, e
    return None


def faithfulness_views(recs, pool, seed=0):
    """Paired (original, edited, technique, kind) cases from dev gold."""
    rng = random.Random(seed)
    cases = []
    for r in recs:
        para = r["paragraph_text"]
        spans = A.base_spans(r)
        occupied = [(s["start"], s["end"]) for s in spans]
        by_t = {}
        for s in spans:
            by_t.setdefault(s["tech"], []).append(s)
        for t, ss in by_t.items():
            if len(ss) != 1:  # kill is only defined when the span is the sole evidence
                continue
            s = ss[0]
            cases.append((para, erase(para, s["start"], s["end"]), t, "kill"))
            c = control_region(para, s["start"], s["end"], occupied, rng)
            if c:
                cases.append((para, erase(para, *c), t, "kill_ctrl"))
            parts = erase(para, s["start"], s["end"]).split(" ")
            parts.insert(rng.randrange(len(parts) + 1), s["text"])
            cases.append((para, " ".join(parts), t, "relocate"))
        present = set(r.get("paragraph_techniques", []))
        if by_t:
            v2 = [v for v in A.make_views(r, pool, rng) if v["view"] == "V2"]
            for v in v2:
                for t in present & set(by_t):
                    cases.append((para, v["text"], t, "distractor"))
    negs = [r for r in recs]
    for t in A.ENGLISH_19:
        cand = [r for r in negs if t not in set(r.get("paragraph_techniques", []))]
        for _ in range(20 if pool.get(t) and cand else 0):
            r = rng.choice(cand)
            para = r["paragraph_text"]
            toks = list(re.finditer(r"\S+", para))
            if not toks:
                continue
            tok = rng.choice(toks)
            cue = rng.choice(pool[t])
            cases.append((para, para[:tok.end()] + " " + cue + " " + para[tok.end():], t,
                           "inject"))
            # matched control: same insertion point, a same-length chunk of NON-evidence text
            # from another paragraph (tests whether p_t reacts to insertion itself)
            chunk = random_nonevidence_chunk(recs, r, len(cue), rng)
            if chunk:
                cases.append((para, para[:tok.end()] + " " + chunk + " " + para[tok.end():],
                              t, "inject_ctrl"))
    return cases


def random_nonevidence_chunk(recs, exclude, n_chars, rng, tries=50):
    """A word-aligned chunk of about n_chars from a random other paragraph, overlapping no
    gold span of that paragraph."""
    for _ in range(tries):
        r = rng.choice(recs)
        if r is exclude:
            continue
        text = r["paragraph_text"]
        if len(text) <= n_chars + 1:
            continue
        occupied = [(s["start"], s["end"]) for s in A.base_spans(r)]
        starts = [m.start() for m in re.finditer(r"(?<=\s)\S", text)]
        rng.shuffle(starts)
        for s in starts[:10]:
            e = text.find(" ", s + n_chars)
            e = len(text) if e < 0 else e
            if e - s <= 1.5 * n_chars + 5 and all(e <= a or s >= b for a, b in occupied):
                return text[s:e]
    return None


V2_FAMILIES = ("KILL", "INJECT", "SWAP", "RELOC", "SUFF")
V2_HELD_OUT = ("RELOC", "SUFF")  # never used as training views


def faithfulness_v2(model, tok, dev, pool, fit, ed_dev, device, seed=0):
    """Artifact-balanced faithfulness (notes/cem_v2_design.md): for each pair, the change in
    p_t caused by the evidence edit minus the change caused by its matched control edit.
    KILL < 0, INJECT > 0, SWAP: t down and t2 up, RELOC ~ 0 (reported as |edit| - |control|),
    SUFF: p_t(evidence span alone) - p_t(same-shape non-evidence text alone) > 0."""
    views = AV.generate(dev, pool, ed_dev, V2_FAMILIES, per_record=1, seed=seed, source_recs=fit)
    pairs = {}
    for v in views:
        pairs.setdefault(v["pair"], []).append(v)
    texts = sorted({v["text"] for v in views} | {v["orig_text"] for v in views})
    pos = {x: k for k, x in enumerate(texts)}
    p_label, q_span = score_texts(model, tok, texts, device)
    out = {"label": _faith_stats(p_label, pairs, pos, seed)}
    if q_span is not None:  # span-grounded channel: the best evidence span's probability
        out["span"] = _faith_stats(q_span, pairs, pos, seed)
    return out


def _faith_stats(p, pairs, pos, seed):
    rows = []
    for pid, vs in pairs.items():
        if len(vs) != 2:
            continue
        ev, ct = vs
        t = A.LAB2ID[ev["tech"]]
        fam = ev["view"]
        po = p[pos[ev["orig_text"]], t]
        if fam == "SUFF":
            de, dc = p[pos[ev["text"]], t], p[pos[ct["text"]], t]
        else:
            de, dc = p[pos[ev["text"]], t] - po, p[pos[ct["text"]], t] - po
        stat = (abs(de) - abs(dc)) if fam == "RELOC" else (de - dc)
        row = {"pair": pid, "family": fam, "tech": ev["tech"], "d_edit": round(float(de), 6),
               "d_ctrl": round(float(dc), 6), "stat": round(float(stat), 6)}
        if fam == "SWAP":
            t2 = A.LAB2ID[ev["tech2"]]
            row["d_new_edit"] = round(float(p[pos[ev["text"]], t2] - p[pos[ev["orig_text"]], t2]), 6)
            row["d_new_ctrl"] = round(float(p[pos[ct["text"]], t2] - p[pos[ct["orig_text"]], t2]), 6)
        rows.append(row)
    rng = np.random.default_rng(seed)
    res = {}
    for fam in V2_FAMILIES:
        x = np.array([r["stat"] for r in rows if r["family"] == fam])
        if not len(x):
            continue
        boots = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(2000)]
        res[fam] = {"n": int(len(x)), "held_out": fam in V2_HELD_OUT,
                    "mean_edit": float(np.mean([r["d_edit"] for r in rows if r["family"] == fam])),
                    "mean_ctrl": float(np.mean([r["d_ctrl"] for r in rows if r["family"] == fam])),
                    "stat": float(x.mean()),
                    "stat_ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]}
        if fam == "SWAP":
            res[fam]["mean_new_edit_minus_ctrl"] = float(np.mean(
                [r["d_new_edit"] - r["d_new_ctrl"] for r in rows if r["family"] == fam]))
    return res, rows


def score_texts(model, tok, texts, device, max_len=512):
    feats = D.encode([{"view": "X", "text": x, "label": [0.0] * T} for x in texts], tok, max_len)
    z, qm, _ = run(model, feats, device)
    return sigmoid(z), qm


def faithfulness(model, tok, cases, device, temp):
    uniq = sorted({c[0] for c in cases} | {c[1] for c in cases})
    pos = {x: k for k, x in enumerate(uniq)}
    p, _ = score_texts(model, tok, uniq, device)
    res, rows = {}, []
    for kind in ("kill", "kill_ctrl", "relocate", "distractor", "inject", "inject_ctrl"):
        d = []
        for n, (a, b, t, k) in enumerate(cases):
            if k == kind:
                d.append(p[pos[b], A.LAB2ID[t]] - p[pos[a], A.LAB2ID[t]])
                rows.append({"case": n, "kind": k, "tech": t,
                             "key": hashlib.md5(a.encode("utf-8")).hexdigest()[:12] + "|" + t,
                             "delta": round(float(d[-1]), 6)})
        if d:
            d = np.array(d)
            res[kind] = {"n": int(len(d)), "mean_delta": float(d.mean()),
                         "mean_abs_delta": float(np.abs(d).mean())}
    return res, rows


def comprehensiveness(model, tok, feats, props, p_label, th, device, seed=0):
    """Erase the model's own top span for each predicted technique vs a same-length random
    non-overlapping region (matched control)."""
    rng = random.Random(seed)
    cases = []
    for k, (pr, f) in enumerate(zip(props, feats)):
        best = {}
        for t, i, j, z in pr or []:
            if p_label[k, int(t)] >= th and (int(t) not in best or z > best[int(t)][0]):
                best[int(t)] = (z, int(i), int(j))
        for t, (_, i, j) in best.items():
            a, b = f["offsets"][i][0], f["offsets"][j - 1][1]
            c = control_region(f["text"], a, b, [(a, b)], rng)
            if c:
                cases.append((f["text"], erase(f["text"], a, b), erase(f["text"], *c), t))
    if not cases:
        return {}
    texts = sorted({x for c in cases for x in c[:3]})
    pos = {x: k for k, x in enumerate(texts)}
    p, _ = score_texts(model, tok, texts, device)
    d_top = np.array([p[pos[o], t] - p[pos[e], t] for o, e, _, t in cases])
    d_ctl = np.array([p[pos[o], t] - p[pos[c], t] for o, _, c, t in cases])
    rng_np = np.random.default_rng(seed)
    boots = [(d_top - d_ctl)[rng_np.integers(0, len(cases), len(cases))].mean()
             for _ in range(2000)]
    return {"n": len(cases), "drop_top_span": float(d_top.mean()),
            "drop_control": float(d_ctl.mean()), "diff": float((d_top - d_ctl).mean()),
            "diff_ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]}


def gpu_busy():
    """Other processes' GPU memory in MiB at timing time (latency is only valid when ~0)."""
    try:
        import subprocess
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,utilization.gpu",
                              "--format=csv,noheader,nounits"], capture_output=True, text=True)
        used, util = [int(x) for x in out.stdout.strip().split(",")]
        return {"memory_used_mib": used, "utilization_pct": util}
    except Exception:
        return None


@torch.no_grad()
def latency(model, tok, texts, device):
    feats = D.encode([{"view": "X", "text": x, "label": [0.0] * T} for x in texts], tok)
    model.eval()
    def one(fs):
        b = D.collate(fs, getattr(model, 'pad_id', 0))
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
            model(b["input_ids"].to(device), b["attention_mask"].to(device))
        if device.type == "cuda":
            torch.cuda.synchronize()
    for f in feats[:20]:
        one([f])
    ts = []
    for f in feats:
        t0 = time.perf_counter(); one([f]); ts.append(time.perf_counter() - t0)
    t0 = time.perf_counter()
    for s in range(0, len(feats), 32):
        one(feats[s:s + 32])
    thr = len(feats) / (time.perf_counter() - t0)
    return {"p50_ms": float(np.percentile(ts, 50) * 1000), "p95_ms": float(np.percentile(ts, 95) * 1000),
            "throughput_para_per_s_bs32": float(thr), "n": len(feats)}


ARGUMENTATIVE = {"Doubt", "Causal_Oversimplification", "Appeal_to_Authority",
                 "False_Dilemma-No_Choice", "Appeal_to_Hypocrisy", "Straw_Man", "Whataboutism",
                 "Appeal_to_Popularity", "Appeal_to_Fear-Prejudice", "Guilt_by_Association"}
LEXICAL = {"Loaded_Language", "Name_Calling-Labeling", "Repetition"}


def evidence_by_group(props, feats):
    """Top-1 hit and recall@3 on gold slots, split into argumentative vs lexical techniques
    (groups fixed in notes/parser_design.md from the chance-controlled alignment table)."""
    res = {}
    for name, group in (("argumentative", ARGUMENTATIVE), ("lexical", LEXICAL)):
        ids = {A.LAB2ID[t] for t in group}
        hit = n = rec = ng = 0
        for pr, f in zip(props, feats):
            by_t = {}
            for t, i, j, z in pr or []:
                by_t.setdefault(int(t), []).append((float(z), int(i), int(j)))
            gold = {}
            for t, i, j in f["spans"]:
                if t in ids:
                    gold.setdefault(t, []).append((i, j))
            for t, gs in gold.items():
                cand = sorted(by_t.get(t, []), reverse=True)
                if not cand:
                    continue
                n += 1
                hit += int(max(iou(cand[0][1], cand[0][2], gi, gj) for gi, gj in gs) >= 0.5)
                for gi, gj in gs:
                    ng += 1
                    rec += int(any(iou(i2, j2, gi, gj) >= 0.5 for _, i2, j2 in cand[:3]))
        res[name] = {"top1_hit": hit / max(1, n), "recall_top3": rec / max(1, ng), "n_slots": n}
    return res


@torch.no_grad()
def segmenter_quality(model, feats, device):
    """Token-level F1 of the distilled segmenter against DMRST silver boundaries (dev)."""
    model.eval()
    tp = fp = fn = 0
    for s in range(0, len(feats), 32):
        batch = D.collate(feats[s:s + 32], getattr(model, 'pad_id', 0))
        if not batch["seg_mask"].any():
            continue
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
            out = model(batch["input_ids"].to(device), batch["attention_mask"].to(device))
        pred = (torch.sigmoid(out["seg_logits"].float()).cpu() >= 0.5)
        gold = batch["seg"] > 0.5
        m = batch["seg_mask"].unsqueeze(-1).expand_as(gold)
        tp += int((pred & gold & m).sum()); fp += int((pred & ~gold & m).sum())
        fn += int((~pred & gold & m).sum())
    return {"boundary_f1": 2 * tp / max(1, 2 * tp + fp + fn), "tp": tp, "fp": fp, "fn": fn}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--no-latency", action="store_true",
                    help="skip timing (use when another job shares the GPU)")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    out = a.out or a.ckpt.parent / "eval"
    out.mkdir(parents=True, exist_ok=True)
    device = torch.device(("cuda" if torch.cuda.is_available() else "cpu")
                          if a.device == "auto" else a.device)
    ck = torch.load(a.ckpt, map_location="cpu", weights_only=False)
    arm = ck["config"]["arm"]
    backbone = ck["config"].get("backbone", BACKBONE)
    parser = ck["config"].get("parser", "none")
    model = JevPersuader(backbone=backbone, evidence=(arm == "cea"), parser=parser)
    model.load_state_dict(ck["model"])
    model.to(device)
    tok = AutoTokenizer.from_pretrained(backbone)
    model.pad_id = tok.pad_token_id

    train = D.load(D.TRAIN_ALL)
    fit, hold = D.split_by_article(train)
    dev = D.load(D.DEV_ALL)
    if a.limit:
        hold, dev = hold[:a.limit], dev[:a.limit]
    # silver EDUs for every model: segmenter quality (parser models) and oracle structural
    # candidates (all evidence models); they never enter a non-parser model's forward pass
    ed_tr, ed_dev = E.load("train"), E.load("dev")
    hf, df = D.encode(D.plain_views(hold), tok, edus=ed_tr), D.encode(D.plain_views(dev), tok, edus=ed_dev)
    yh = np.stack([f["label"].numpy() for f in hf]); yd = np.stack([f["label"].numpy() for f in df])
    zh, qh, ph = run(model, hf, device, keep_spans=True)
    zd, qd, pd = run(model, df, device, keep_spans=True)

    m = {"eval_version": EVAL_VERSION, "ckpt": str(a.ckpt), "arm": arm, "cem": not ck["config"].get("no_cem", False),
         "backbone": backbone, "parser": parser,
         "seed": ck["config"]["seed"], "best_epoch": ck.get("epoch"),
         "n_holdout": len(hf), "n_dev": len(df)}
    th = best_threshold(sigmoid(zh), yh)
    m["label_mode"] = dict(zip(("micro_f1", "macro_f1"), f1s(sigmoid(zd), yd, th)), threshold=th)
    temp = fit_temperature(zh, yh)
    m["label_calibration"] = calib(zd, yd, temp)
    m["selective"] = selective(sigmoid(zd / temp), yd, best_threshold(sigmoid(zh / temp), yh))
    if model.evidence:
        ths = best_threshold(qh, yh)
        m["span_mode"] = dict(zip(("micro_f1", "macro_f1"), f1s(qd, yd, ths)), threshold=ths)
        zeh, yeh = proposal_arrays(ph, hf)
        zed, yed = proposal_arrays(pd, df)
        etemp = fit_temperature(zeh, yeh)
        m["evidence_calibration"] = calib(zed, yed, etemp)
        m["cited_span_calibration"] = cited_span_calibration(
            cited_arrays(ph, hf, sigmoid(zh), th), cited_arrays(pd, df, sigmoid(zd), th), etemp)
        m["evidence_calibration"]["n_proposals"] = int(len(yed))
        m["evidence_calibration"]["positive_rate"] = float(yed.mean())
        m["evidence"] = evidence_scores(pd, df, sigmoid(zd), th)
        m["comprehensiveness"] = comprehensiveness(model, tok, df, pd, sigmoid(zd), th, device)
    if parser != "none" and df:
        m["segmenter"] = segmenter_quality(model, df, device)
    if parser == "prior" and model.evidence:
        m["gates"] = {A.ENGLISH_19[t]: [round(float(model.gate[0, t]), 4),
                                        round(float(model.gate[1, t]), 4)] for t in range(T)}
        m["prior_modes"] = {}
        for mode in ("oracle", "shift", "zero"):
            model.prior_mode = mode
            zm, qm, pm = run(model, df, device, keep_spans=True)
            m["prior_modes"][mode] = {
                "micro_f1": f1s(sigmoid(zm), yd, th)[0],
                "span_mode_micro_f1": f1s(qm, yd, m["span_mode"]["threshold"])[0],
                **evidence_scores(pm, df, sigmoid(zm), th),
                "by_group": evidence_by_group(pm, df)}
        model.prior_mode = "pred"
    if model.evidence:
        m["evidence_by_group"] = evidence_by_group(pd, df)
        # structural candidates (runs of 1-3 EDUs) added at inference, no retraining:
        # oracle = DMRST boundaries (external parser), pred = the model's own segmenter
        m["struct_candidates"] = {}
        for mode in (("oracle", "pred") if parser != "none" else ("oracle",)):
            model.struct_mode = mode
            zs, qs, ps = run(model, df, device, keep_spans=True)
            m["struct_candidates"][mode] = {
                "micro_f1": f1s(sigmoid(zs), yd, th)[0],
                "span_mode_micro_f1": f1s(qs, yd, m["span_mode"]["threshold"])[0],
                **evidence_scores(ps, df, sigmoid(zs), th), "by_group": evidence_by_group(ps, df)}
        model.struct_mode = "none"
    pool = A.build_pool(fit)
    m["faithfulness"], faith_rows = faithfulness(model, tok, faithfulness_views(dev, pool),
                                                 device, temp)
    # insertion material for dev edits comes from OTHER dev paragraphs' gold spans and text,
    # never from the train pool the CEM models saw inserted (that would test memorisation)
    fv2 = faithfulness_v2(model, tok, dev, A.build_pool(dev), dev, E.load("dev"), device)
    m["faithfulness_v2"], v2_rows = fv2["label"]
    with (out / "faith_v2_pairs.jsonl").open("w", encoding="utf-8") as f:
        for r in v2_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    if "span" in fv2:  # same tests on the span-grounded decision (max evidence probability)
        m["faithfulness_v2_span"], span_rows = fv2["span"]
        with (out / "faith_v2_span_pairs.jsonl").open("w", encoding="utf-8") as f:
            for r in span_rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with (out / "faith_cases.jsonl").open("w", encoding="utf-8") as f:
        for r in faith_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    if device.type == "cuda" and not a.no_latency:
        m["latency"] = latency(model, tok, [f["text"] for f in df[:300]], device)
        m["latency"]["gpu_busy_before"] = gpu_busy()

    with (out / "preds_dev.jsonl").open("w", encoding="utf-8") as f:
        for k, fe in enumerate(df):
            rec = {"id": dev[k]["id"], "p": [round(float(x), 4) for x in sigmoid(zd[k])],
                   "gold": [A.ENGLISH_19[t] for t in np.where(yd[k] > 0.5)[0]]}
            if model.evidence:
                cites = {}
                for t, i, j, z in sorted(pd[k] or [], key=lambda x: -x[3]):
                    name = A.ENGLISH_19[int(t)]
                    if len(cites.setdefault(name, [])) < 3:
                        a0, b0 = fe["offsets"][int(i)][0], fe["offsets"][int(j) - 1][1]
                        cites[name].append({"text": fe["text"][a0:b0], "start": a0, "end": b0,
                                            "q": round(float(sigmoid(z)), 4)})
                rec["qmax"] = [round(float(x), 4) for x in qd[k]]
                rec["cites"] = {t: c for t, c in cites.items()
                                if sigmoid(zd[k][A.LAB2ID[t]]) >= th}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    (out / "metrics.json").write_text(json.dumps(m, indent=2))
    print(json.dumps(m, indent=2))


if __name__ == "__main__":
    main()
