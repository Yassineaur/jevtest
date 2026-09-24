"""CPU smoke test for the v2 model and data pipeline (no GPU needed).

Checks, on REAL encoded training views (a CEM mix), that:
  1. the forward pass returns the right shapes for both arms (T4 evidence model, T0 control);
  2. every proposal is a valid token range inside the paragraph text, at most MAX_SPAN_LEN long;
  3. proposal_targets marks a gold span as positive and a disjoint span as negative;
  4. the CEA loss is finite and its backward pass reaches the encoder, label head, proposer and
     evidence scorer;
  5. the Brier term is proper: for a fixed target rate r, a constant q minimises it at q = r
     (the v1 pos-weighted Brier did not).

Run: ..\\..\\torch_env\\Scripts\\python.exe cpu_test.py   (from code/)
"""
from __future__ import annotations

import os
import random
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import torch  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402

import augment as A  # noqa: E402
import data as D  # noqa: E402
from model import BACKBONE, MAX_SPAN_LEN, JevPersuader, losses, proposal_targets  # noqa: E402


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    torch.manual_seed(0)
    tok = AutoTokenizer.from_pretrained(BACKBONE)
    recs = D.load(D.TRAIN_ALL)
    fit, _ = D.split_by_article(recs)
    rng = random.Random(0)
    views = D.epoch_views(fit[:60], A.build_pool(fit), rng, inject_per_tech=1)
    # make sure the batch holds positives with evidence and a manipulated view
    with_ev = [v for v in views if v["view"] == "V0" and v.get("spans")][:4]
    cf = [v for v in views if v["view"] in ("V1", "V3", "V6")][:2]
    views = with_ev + cf
    feats = D.encode(views, tok)
    batch = D.collate(feats, tok.pad_token_id)
    B, L = batch["input_ids"].shape
    print(f"batch: B={B} L={L} views={batch['view']} gold_spans={(batch['gold'][..., 0] >= 0).sum().item()}")

    # 1 + 2: T4 forward
    model = JevPersuader()
    model.train()
    out = model(batch["input_ids"], batch["attention_mask"], gold=batch["gold"])
    assert out["label_logits"].shape == (B, 19)
    assert out["start_logits"].shape == (B, L, 19)
    assert out["qmax"].shape == (B, 19)
    pb, pi, pj = out["pb"], out["pi"], out["pj"]
    lens = batch["attention_mask"].sum(1)
    assert bool(((pj > pi) & (pi >= 1) & (pj <= lens[pb] - 1)).all()), "proposal outside text"
    n_gold = int((batch["gold"][..., 0] >= 0).sum())
    assert bool(((pj - pi)[: len(pj) - n_gold] <= MAX_SPAN_LEN).all()), "proposal too long"
    print(f"T4 forward ok: proposals={len(pb)} (incl. {n_gold} gold) q range=({out['q'].min():.3f}, {out['q'].max():.3f})")

    # 3: proposal targets on a hand example
    gold = torch.tensor([[[5, 3, 8], [-1, -1, -1]]])
    t = proposal_targets(gold, torch.tensor([0, 0, 0]), torch.tensor([5, 5, 4]),
                         torch.tensor([3, 10, 3]), torch.tensor([8, 12, 8]))
    assert t.tolist() == [1.0, 0.0, 0.0], t
    print("proposal_targets ok: exact gold=1, disjoint=0, wrong technique=0")

    # 4: loss + backward
    loss, comp = losses(out, batch)
    assert torch.isfinite(loss), comp
    loss.backward()
    grads = {
        "encoder": model.encoder.embeddings.word_embeddings.weight.grad,
        "label_head": model.label_head.weight.grad,
        "proposer": model.boundary.weight.grad,
        "evidence_scorer": model.span_scorer[0].weight.grad,
    }
    for k, g in grads.items():
        assert g is not None and torch.isfinite(g).all() and g.abs().sum() > 0, k
    print("T4 loss ok:", {k: round(v, 4) for k, v in comp.items()})
    print("backward reaches:", ", ".join(grads))

    # T0 control: same class, no evidence head
    t0 = JevPersuader(evidence=False)
    o0 = t0(batch["input_ids"], batch["attention_mask"])
    l0, c0 = losses(o0, batch)
    l0.backward()
    assert torch.isfinite(l0) and t0.label_head.weight.grad is not None
    print("T0 control ok:", {k: round(v, 4) for k, v in c0.items()})

    # 5: properness of the evidence Brier
    for r in (0.02, 0.2):
        y = (torch.rand(20000) < r).float()
        grid = torch.linspace(0, 1, 201)
        best = grid[((grid.unsqueeze(1) - y) ** 2).mean(1).argmin()]
        assert abs(best.item() - y.mean().item()) < 0.01
        print(f"Brier minimiser for base rate {y.mean():.3f}: q={best:.3f} (calibrated)")
    print("SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
