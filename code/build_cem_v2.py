"""Build the frozen, fluency-filtered CEM v2 training pool (notes/cem_v2_design.md).

Steps (train-FIT split only; dev and holdout are never touched):
  1. generate KILL / INJECT / SWAP pairs (edit + matched control), 2 attempts per paragraph;
  2. cap reuse of any inserted gold string at MAX_CUE_USES (rare techniques have 15-50 spans;
     unlimited reuse would let the model memorise strings instead of techniques);
  3. score every original and edited text with GPT-2 (mean token NLL) and keep a PAIR only if
     both its edit and its control raise NLL by at most TAU nats per token over the original;
  4. report, per family, pass rates for edits and controls and the AUC with which the NLL
     increase separates edits from controls before and after filtering (0.5 = indistinguishable);
  5. write data/cem_v2_pool.jsonl and data/cem_v2_pool.meta.json (SHA-256, counts, TAU, report).

TAU is fixed in advance at 0.30 nats/token (about a 35% perplexity increase), a bound on how
much less natural an edited paragraph may be; the report shows how much it removes.
Run: ..\\..\\torch_env\\Scripts\\python.exe build_cem_v2.py  (GPU if free, else CPU)
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parent))
import augment as A  # noqa: E402
import augment_v2 as V  # noqa: E402
import data as D  # noqa: E402
import edus as E  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TAU = 0.30
MAX_CUE_USES = 5
LM = "openai-community/gpt2"


@torch.no_grad()
def nll_scores(texts, device, batch=16):
    tok = AutoTokenizer.from_pretrained(LM)
    tok.pad_token = tok.eos_token
    lm = AutoModelForCausalLM.from_pretrained(LM).to(device).eval()
    out = {}
    uniq = sorted(set(texts), key=len)
    for s in range(0, len(uniq), batch):
        chunk = uniq[s:s + batch]
        enc = tok([tok.bos_token + t for t in chunk], return_tensors="pt", padding=True,
                  truncation=True, max_length=512).to(device)
        logits = lm(**enc).logits[:, :-1]  # no float32 copy: memory-safe next to training
        tgt = enc["input_ids"][:, 1:]
        m = enc["attention_mask"][:, 1:].float()
        ce = torch.nn.functional.cross_entropy(logits.transpose(1, 2), tgt,
                                               reduction="none").float()
        per = (ce * m).sum(1) / m.sum(1).clamp(min=1)
        for t, v in zip(chunk, per.tolist()):
            out[t] = v
        if s % (batch * 100) == 0:
            print(f"  scored {s + len(chunk)}/{len(uniq)}", flush=True)
    return out


def auc(pos, neg):
    """P(score_pos > score_neg) (ties half), i.e. how well the NLL increase flags the edit."""
    if not pos or not neg:
        return float("nan")
    x = np.array(pos)[:, None]
    y = np.array(neg)[None, :]
    return float(((x > y).mean() + 0.5 * (x == y).mean()))


DELTA = 0.10  # max |dNLL(edit) - dNLL(control)| within a pair (fluency matching)


def rebalance(delta: float = DELTA) -> None:
    """Fluency-match pairs in the existing pool: keep a pair only if its edit and control
    changed the GPT-2 NLL by amounts within `delta` of each other, so fluency cannot tell an
    evidence edit from its control. The unmatched pool is kept as cem_v2_pool_unmatched.jsonl."""
    src = ROOT / "data" / "cem_v2_pool.jsonl"
    meta_p = ROOT / "data" / "cem_v2_pool.meta.json"
    meta = json.loads(meta_p.read_text())
    if meta.get("fluency_matched"):
        print("pool already fluency-matched"); return
    keep_copy = ROOT / "data" / "cem_v2_pool_unmatched.jsonl"
    keep_copy.write_bytes(src.read_bytes())
    pairs = collections.OrderedDict()
    for line in src.open(encoding="utf-8"):
        v = json.loads(line)
        pairs.setdefault(v["pair"], []).append(v)
    report = {}
    kept = []
    for fam in V.TRAIN_FAMILIES:
        ps = [vs for vs in pairs.values() if len(vs) == 2 and vs[0]["view"] == fam]
        ok = [vs for vs in ps if abs(vs[0]["dnll"] - vs[1]["dnll"]) <= delta]
        kept += ok
        report[fam] = {"pairs_in": len(ps), "pairs_kept": len(ok),
                       "auc_after_matching": auc([a["dnll"] for a, _ in ok], [b["dnll"] for _, b in ok]),
                       "median_dNLL_edit": float(np.median([a["dnll"] for a, _ in ok])) if ok else None,
                       "median_dNLL_control": float(np.median([b["dnll"] for _, b in ok])) if ok else None}
    with src.open("w", encoding="utf-8") as f:
        for vs in kept:
            for v in vs:
                f.write(json.dumps(v, ensure_ascii=False) + "\n")
    meta["report_prefilter"] = meta.pop("report")
    meta.update({"fluency_matched": True, "delta": delta, "pairs": len(kept), "views": 2 * len(kept),
                 "sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
                 "sha256_unmatched": hashlib.sha256(keep_copy.read_bytes()).hexdigest(),
                 "report": report})
    meta_p.write_text(json.dumps(meta, indent=2))
    print(json.dumps(report, indent=2))
    print("pairs kept", len(kept))


def exclude_inserted(techs=frozenset(V.NO_INSERT)) -> None:
    """Drop pool pairs whose INSERTED technique is definitionally impossible to create by one
    insertion (INJECT tech, or SWAP tech2). Records counts and the new hash in the meta."""
    src = ROOT / "data" / "cem_v2_pool.jsonl"
    meta_p = ROOT / "data" / "cem_v2_pool.meta.json"
    meta = json.loads(meta_p.read_text())
    pairs = collections.OrderedDict()
    for line in src.open(encoding="utf-8"):
        v = json.loads(line)
        pairs.setdefault(v["pair"], []).append(v)
    D.fill_tech2(pairs.values())
    dropped = collections.Counter()
    kept = []
    for vs in pairs.values():
        ev = vs[0]
        ins = ev["tech"] if ev["view"] == "INJECT" else ev.get("tech2") if ev["view"] == "SWAP" else None
        if ins in techs:
            dropped[ev["view"]] += 1
            continue
        kept.append(vs)
    with src.open("w", encoding="utf-8") as f:
        for vs in kept:
            for v in vs:
                f.write(json.dumps(v, ensure_ascii=False) + "\n")
    meta.update({"excluded_inserted_techniques": sorted(techs), "excluded_pairs": dict(dropped),
                 "pairs": len(kept), "views": 2 * len(kept),
                 "sha256": hashlib.sha256(src.read_bytes()).hexdigest()})
    meta_p.write_text(json.dumps(meta, indent=2))
    print("dropped", dict(dropped), "pairs kept", len(kept))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--per-record", type=int, default=2)
    ap.add_argument("--rebalance", action="store_true", help="fluency-match the existing pool")
    ap.add_argument("--exclude-inserted", action="store_true",
                    help="drop pairs inserting a definitionally context-dependent technique")
    ap.add_argument("--device", default="cpu",
                    help="cpu by default so fluency scoring never competes with GPU training")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if a.rebalance:
        rebalance()
        return
    if a.exclude_inserted:
        exclude_inserted()
        return
    recs = D.load(D.TRAIN_ALL)
    fit, _ = D.split_by_article(recs)
    pool = A.build_pool(fit)
    edus = E.load("train")
    views = V.generate(fit, pool, edus, V.TRAIN_FAMILIES, per_record=a.per_record, seed=a.seed)
    assert V.validate(views) == 0
    pairs = collections.OrderedDict()
    for v in views:
        pairs.setdefault(v["pair"], []).append(v)
    pairs = {k: vs for k, vs in pairs.items() if len(vs) == 2}
    # dedupe identical edits (two attempts can produce the same splice)
    seen, uniq = set(), {}
    for k, (ev, ct) in pairs.items():
        sig = (ev["text"], ct["text"])
        if sig not in seen:
            seen.add(sig)
            uniq[k] = (ev, ct)
    # cue reuse cap
    uses = collections.Counter()
    capped = {}
    for k, (ev, ct) in uniq.items():
        cue = None
        if ev["view"] in ("INJECT", "SWAP"):
            cue = ev["spans"][-1]["text"] if ev["evidence_present"] and ev["spans"] else ev["text"]
        if cue is not None:
            uses[cue] += 1
            if uses[cue] > MAX_CUE_USES:
                continue
        capped[k] = (ev, ct)
    print(f"pairs generated {len(pairs)}, unique {len(uniq)}, after cue cap {len(capped)}")

    texts = [v["text"] for p in capped.values() for v in p] + [p[0]["orig_text"] for p in capped.values()]
    nll = nll_scores(texts, torch.device(a.device))
    report, kept = {}, []
    for fam in V.TRAIN_FAMILIES:
        ps = [(ev, ct) for ev, ct in capped.values() if ev["view"] == fam]
        de = [nll[ev["text"]] - nll[ev["orig_text"]] for ev, _ in ps]
        dc = [nll[ct["text"]] - nll[ct["orig_text"]] for _, ct in ps]
        keep = [i for i in range(len(ps)) if de[i] <= TAU and dc[i] <= TAU]
        kept += [ps[i] for i in keep]
        report[fam] = {
            "pairs": len(ps), "kept_pairs": len(keep),
            "edit_pass": float(np.mean([x <= TAU for x in de])) if de else None,
            "control_pass": float(np.mean([x <= TAU for x in dc])) if dc else None,
            "median_dNLL_edit": float(np.median(de)) if de else None,
            "median_dNLL_control": float(np.median(dc)) if dc else None,
            "auc_before": auc(de, dc),
            "auc_after": auc([de[i] for i in keep], [dc[i] for i in keep]),
        }
    out = ROOT / "data" / "cem_v2_pool.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for ev, ct in kept:
            for v in (ev, ct):
                v = dict(v)
                v["dnll"] = round(nll[v["text"]] - nll[v["orig_text"]], 4)
                v.pop("orig_text", None)
                f.write(json.dumps(v, ensure_ascii=False) + "\n")
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    meta = {"sha256": sha, "tau": TAU, "max_cue_uses": MAX_CUE_USES, "lm": LM, "seed": a.seed,
            "per_record": a.per_record, "pairs": len(kept), "views": 2 * len(kept),
            "split": "train-fit (article-level, data.split_by_article seed 0)", "report": report}
    (ROOT / "data" / "cem_v2_pool.meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
