"""SFT training for jevpersuation (T4 = CEA with evidence, T0 = label-only control).

Both arms see the SAME views (CEM mix by default) and share encoder, label head, optimiser and
schedule; the only difference is the evidence channel (proposer + evidence scorer + its losses).

Resumable (research-pipeline references/resumability.md): each epoch's views and batch order are
rebuilt deterministically from (seed, epoch), a full checkpoint (model, optimiser, scheduler, step)
is written atomically every --ckpt-every steps and at every epoch end, and a rerun continues from
the last saved step. A finished run writes <out>/DONE and a rerun exits immediately.

Model selection uses the article-level holdout cut from train (never dev): micro-F1 at the best
global threshold of the full-text label head.

Examples (from the project root):
  ..\\torch_env\\Scripts\\python.exe code\\train.py --arm cea   --seed 0 --out results\\pilot\\T4_s0
  ..\\torch_env\\Scripts\\python.exe code\\train.py --arm label --seed 0 --out results\\pilot\\T0_s0
  ... --limit 64 --epochs 1        (smoke test)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import torch
from transformers import AutoTokenizer, get_linear_schedule_with_warmup

sys.path.insert(0, str(Path(__file__).resolve().parent))
import augment as A  # noqa: E402
import data as D  # noqa: E402
import edus as E  # noqa: E402
from model import BACKBONE, JevPersuader, losses  # noqa: E402


def micro_f1_best(p: np.ndarray, y: np.ndarray):
    """Micro-F1 at the best global threshold on a 0.05 grid. Returns (f1, threshold)."""
    best = (0.0, 0.5)
    for th in np.arange(0.05, 0.96, 0.05):
        pred = p >= th
        tp = float((pred & (y > 0.5)).sum())
        fp = float((pred & (y < 0.5)).sum())
        fn = float((~pred & (y > 0.5)).sum())
        f1 = 2 * tp / max(1.0, 2 * tp + fp + fn)
        if f1 > best[0]:
            best = (f1, float(th))
    return best


@torch.no_grad()
def evaluate_holdout(model, feats, batch_size, pad_id, device):
    model.eval()
    P, Q, Y = [], [], []
    for batch in D.batches(feats, batch_size, rng=None, pad_id=pad_id):
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
            out = model(batch["input_ids"].to(device), batch["attention_mask"].to(device))
        P.append(torch.sigmoid(out["label_logits"].float()).cpu())
        if "qmax" in out:
            Q.append(out["qmax"].float().cpu())
        Y.append(batch["label"])
    model.train()
    p, y = torch.cat(P).numpy(), torch.cat(Y).numpy()
    res = {"f1_label": micro_f1_best(p, y)}
    if Q:
        res["f1_span"] = micro_f1_best(torch.cat(Q).numpy(), y)
    return res


def save_atomic(obj, path: Path):
    tmp = path.with_suffix(path.suffix + ".tmp")
    torch.save(obj, tmp)
    os.replace(tmp, path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=("cea", "label"), required=True)
    ap.add_argument("--no-cem", action="store_true", help="train on V0 views only (ablation)")
    ap.add_argument("--cem", choices=("v1", "v2"), default="v1",
                    help="v1 = augment.py (pilot); v2 = frozen artifact-balanced pool")
    ap.add_argument("--pairs-per-epoch", type=int, default=6000)
    ap.add_argument("--soft-json", type=Path, default=None,
                    help="audited validity per v2 family, e.g. results/cem_audit/soft_targets.json")
    ap.add_argument("--parser", choices=("none", "multitask", "prior"), default="none",
                    help="discourse segmenter head: none | multitask (control) | prior (coupled)")
    ap.add_argument("--seg-weight", type=float, default=1.0)
    ap.add_argument("--backbone", default=BACKBONE)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--patience", type=int, default=2)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--grad-accum", type=int, default=1,
                    help="accumulate gradients over N batches (effective batch = batch-size x N)")
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--head-lr", type=float, default=1e-4)
    ap.add_argument("--warmup", type=float, default=0.06)
    ap.add_argument("--max-len", type=int, default=512)
    ap.add_argument("--alpha", type=float, default=1.0)
    ap.add_argument("--beta", type=float, default=0.1)
    ap.add_argument("--gamma", type=float, default=1.0)
    ap.add_argument("--max-cf-per-record", type=int, default=3)
    ap.add_argument("--inject-per-tech", type=int, default=100)
    ap.add_argument("--ckpt-every", type=int, default=500)
    ap.add_argument("--limit", type=int, default=0, help="smoke test: use N fit records")
    ap.add_argument("--keep-last", action="store_true", help="keep last.pt after DONE")
    ap.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    out = a.out
    out.mkdir(parents=True, exist_ok=True)
    if (out / "DONE").exists():
        print(f"{out} already DONE; nothing to do")
        return
    cfg = vars(a).copy()
    cfg["out"] = str(out)
    cfg_path = out / "config.json"
    if cfg_path.exists():
        old = json.loads(cfg_path.read_text())
        diff = {k: (old.get(k), v) for k, v in cfg.items()
                if old.get(k) != v and k not in ("keep_last", "device", "ckpt_every")}
        if diff:
            raise SystemExit(f"config differs from the run being resumed: {diff}")
    cfg_path.write_text(json.dumps(cfg, indent=2))

    if a.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(a.device)
    torch.backends.cuda.matmul.allow_tf32 = False  # DeBERTa: keep TF32 off (docs/MACHINE.md)
    torch.backends.cudnn.allow_tf32 = False
    random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed)

    tok = AutoTokenizer.from_pretrained(a.backbone)
    recs = D.load(D.TRAIN_ALL)
    fit, hold = D.split_by_article(recs)  # fixed split (seed 0) across all runs
    if a.limit:
        fit, hold = fit[:a.limit], hold[:max(16, a.limit // 4)]
    pool = A.build_pool(fit)
    edus = E.load("train") if a.parser != "none" else None
    hold_feats = D.encode(D.plain_views(hold), tok, a.max_len, edus)

    v2_pairs = D.load_cem_v2_pool() if (a.cem == "v2" and not a.no_cem) else None
    soft = json.loads(a.soft_json.read_text()) if a.soft_json else None
    if v2_pairs is not None:
        print(f"CEM v2 pool: {len(v2_pairs)} pairs, sha256 "
              f"{json.loads((D.ROOT / 'data' / 'cem_v2_pool.meta.json').read_text())['sha256'][:12]}")

    def epoch_feats(epoch: int):
        """Views and batch-order seed for one epoch, a pure function of (seed, epoch)."""
        rng = random.Random(a.seed * 1000 + epoch)
        if v2_pairs is not None:
            views = D.epoch_views_v2(fit, v2_pairs, rng, a.pairs_per_epoch, soft)
            return D.encode(views, tok, a.max_len, edus), rng.random()
        views = D.epoch_views(fit, pool, rng, use_cem=not a.no_cem,
                              max_cf_per_record=a.max_cf_per_record,
                              inject_per_tech=a.inject_per_tech if not a.limit else 2)
        return D.encode(views, tok, a.max_len, edus), rng.random()

    feats0, bseed0 = epoch_feats(0)
    steps_per_epoch = math.ceil(len(feats0) / a.batch_size)
    total_steps = math.ceil(steps_per_epoch / a.grad_accum) * a.epochs  # optimiser steps

    model = JevPersuader(backbone=a.backbone, evidence=(a.arm == "cea"), parser=a.parser).to(device)
    enc_params = list(model.encoder.parameters())
    enc_ids = {id(p) for p in enc_params}
    head_params = [p for p in model.parameters() if id(p) not in enc_ids]
    opt = torch.optim.AdamW([{"params": enc_params, "lr": a.lr},
                             {"params": head_params, "lr": a.head_lr}],
                            weight_decay=0.01, fused=device.type == "cuda")
    sched = get_linear_schedule_with_warmup(opt, int(a.warmup * total_steps), total_steps)

    state = {"epoch": 0, "step_in_epoch": 0, "global_step": 0, "best": -1.0, "bad_epochs": 0}
    last = out / "last.pt"
    if last.exists():
        ck = torch.load(last, map_location="cpu", weights_only=False)
        model.load_state_dict(ck["model"])
        opt.load_state_dict(ck["opt"])
        sched.load_state_dict(ck["sched"])
        state = ck["state"]
        print(f"resumed from {last}: {state}")

    def checkpoint():
        # disk guard: the resume checkpoint holds weights + AdamW moments (~12 bytes/param);
        # skip it (with a warning) rather than fill the disk, which would kill the run
        need = 12 * sum(p.numel() for p in model.parameters()) + 2 * 1024 ** 3
        if shutil.disk_usage(out).free < need:
            print(f"WARNING: low disk ({shutil.disk_usage(out).free / 1e9:.1f} GB free); "
                  "resume checkpoint skipped", flush=True)
            return
        save_atomic({"model": model.state_dict(), "opt": opt.state_dict(),
                     "sched": sched.state_dict(), "state": state}, last)

    log_path = out / "log.jsonl"
    print(f"arm={a.arm} cem={not a.no_cem} fit={len(fit)} holdout={len(hold)} "
          f"views/epoch~{len(feats0)} steps/epoch={steps_per_epoch} device={device}", flush=True)
    model.train()
    opt.zero_grad(set_to_none=True)
    pending = False
    while state["epoch"] < a.epochs and state["bad_epochs"] < a.patience:
        ep = state["epoch"]
        feats, bseed = (feats0, bseed0) if ep == 0 else epoch_feats(ep)
        batch_rng = random.Random(bseed)
        sums, n, t0 = {}, 0, time.time()
        for k, batch in enumerate(D.batches(feats, a.batch_size, batch_rng, tok.pad_token_id)):
            if k < state["step_in_epoch"]:
                continue  # resume inside an epoch
            gold = batch["gold"].to(device)
            b = {kk: (v.to(device) if torch.is_tensor(v) else v) for kk, v in batch.items()}
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
                o = model(b["input_ids"], b["attention_mask"],
                          gold=gold if a.arm == "cea" else None)
            loss, comp = losses(o, b, alpha=a.alpha, beta=a.beta, gamma=a.gamma,
                                seg_weight=a.seg_weight)
            if not torch.isfinite(loss):
                raise SystemExit(f"non-finite loss at epoch {ep} step {k}: {comp}")
            # gradient accumulation: batch_size x grad_accum = the effective batch; with
            # grad_accum 1 this is exactly the original single-batch update
            (loss / a.grad_accum).backward()
            pending = True
            if (k + 1) % a.grad_accum == 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                opt.step()
                sched.step()
                opt.zero_grad(set_to_none=True)
                pending = False
            state["step_in_epoch"] = k + 1
            state["global_step"] += 1
            for kk, v in comp.items():
                sums[kk] = sums.get(kk, 0.0) + v
            n += 1
            if state["global_step"] % 100 == 0:
                rate = n / max(1e-6, time.time() - t0)
                print(f"  ep{ep} step {k + 1}/{steps_per_epoch} "
                      + " ".join(f"{kk}={sums[kk] / n:.4f}" for kk in ("label", "evidence",
                                                                     "boundary", "segment")
                                 if kk in sums)
                      + f" {rate:.1f} it/s", flush=True)
            if state["global_step"] % a.ckpt_every == 0:
                checkpoint()
        if a.grad_accum > 1 and pending:  # flush a partial accumulation group at epoch end
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            opt.zero_grad(set_to_none=True)
        # end of epoch: holdout selection
        res = evaluate_holdout(model, hold_feats, 32, tok.pad_token_id, device)
        f1 = res["f1_label"][0]
        improved = f1 > state["best"]
        if improved:
            need = 4 * sum(p.numel() for p in model.parameters()) + 1024 ** 3
            if shutil.disk_usage(out).free < need:
                raise SystemExit(f"STOP: not enough disk to save best.pt safely "
                                 f"({shutil.disk_usage(out).free / 1e9:.1f} GB free); free space "
                                 "and rerun (the run resumes from its last checkpoint)")
            state["best"], state["bad_epochs"] = f1, 0
            save_atomic({"model": model.state_dict(), "config": cfg, "epoch": ep,
                         "holdout": res}, out / "best.pt")
        else:
            state["bad_epochs"] += 1
        rec = {"epoch": ep, "train": {kk: v / max(1, n) for kk, v in sums.items()},
               "holdout": res, "improved": improved, "minutes": (time.time() - t0) / 60}
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"epoch {ep}: holdout {res} improved={improved}", flush=True)
        state["epoch"] += 1
        state["step_in_epoch"] = 0
        checkpoint()

    (out / "DONE").write_text(json.dumps({"finished": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                          "best_holdout_f1": state["best"],
                                          "epochs_run": state["epoch"]}))
    if not a.keep_last and last.exists():
        last.unlink()
    print(f"DONE: best holdout micro-F1 {state['best']:.4f}")


if __name__ == "__main__":
    main()
