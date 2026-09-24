"""Is discourse segmentation already linearly readable from encoders that never saw a parser?

Explains the coupled-parser null (results/parser/T4disc_s0: gates ~0, oracle = shift = zero):
if EDU boundaries are linearly decodable from the hidden states the span proposer already reads,
a segmenter head coupled on those same states adds no information.

Linear probes (one logistic unit per boundary type: EDU start, EDU end) on frozen token states,
fitted on the train HOLDOUT paragraphs and scored on dev against DMRST silver boundaries, for:
  pretrained  microsoft/deberta-v3-base, no fine-tuning
  T4          our evidence model without any parser (results/pilot/T4_s0/best.pt)
Reference: the trained segmenter head of T4seg reaches boundary F1 0.909 on dev.
Writes results/probe_edu.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch
from transformers import AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data as D  # noqa: E402
import edus as E  # noqa: E402
from model import BACKBONE, JevPersuader  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


@torch.no_grad()
def states(model, feats, device):
    X, Y = [], []
    model.eval()
    for s in range(0, len(feats), 32):
        fs = [f for f in feats[s:s + 32] if f["seg"] is not None]
        if not fs:
            continue
        b = D.collate(fs)
        with torch.autocast("cuda", dtype=torch.bfloat16):
            h = model.encoder(input_ids=b["input_ids"].to(device),
                              attention_mask=b["attention_mask"].to(device)).last_hidden_state
        m = b["seg_mask"]
        X.append(h.float().cpu()[m])
        Y.append(b["seg"][m])
    return torch.cat(X), torch.cat(Y)


def fit_probe(X, Y, epochs=200):
    mu, sd = X.mean(0), X.std(0) + 1e-6
    lin = torch.nn.Linear(X.size(1), 2)
    opt = torch.optim.Adam(lin.parameters(), lr=1e-2, weight_decay=1e-4)
    Xn = (X - mu) / sd
    for _ in range(epochs):
        opt.zero_grad()
        loss = torch.nn.functional.binary_cross_entropy_with_logits(lin(Xn), Y)
        loss.backward()
        opt.step()
    return lambda Z: torch.sigmoid(lin((Z - mu) / sd))


def f1(pred, gold):
    tp = int((pred & gold).sum()); fp = int((pred & ~gold).sum()); fn = int((~pred & gold).sum())
    return 2 * tp / max(1, 2 * tp + fp + fn)


def main() -> None:
    device = torch.device("cuda")
    tok = AutoTokenizer.from_pretrained(BACKBONE)
    train = D.load(D.TRAIN_ALL)
    _, hold = D.split_by_article(train)
    dev = D.load(D.DEV_ALL)
    hf = D.encode(D.plain_views(hold), tok, edus=E.load("train"))
    df = D.encode(D.plain_views(dev), tok, edus=E.load("dev"))
    res = {}
    for name in ("pretrained", "T4"):
        model = JevPersuader(evidence=True)
        if name == "T4":
            ck = torch.load(ROOT / "results/pilot/T4_s0/best.pt", map_location="cpu", weights_only=False)
            model.load_state_dict(ck["model"])
        model.to(device)
        Xh, Yh = states(model, hf, device)
        Xd, Yd = states(model, df, device)
        probe = fit_probe(Xh, Yh)
        P = probe(Xd) >= 0.5
        G = Yd > 0.5
        res[name] = {"start_f1": f1(P[:, 0], G[:, 0]), "end_f1": f1(P[:, 1], G[:, 1]),
                     "boundary_f1": f1(P, G), "n_tokens_fit": int(len(Xh)), "n_tokens_test": int(len(Xd))}
        print(name, res[name], flush=True)
        del model
        torch.cuda.empty_cache()
    res["reference_trained_segmenter_T4seg"] = 0.909
    (ROOT / "results" / "probe_edu.json").write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
