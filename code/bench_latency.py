"""Latency of our checkpoints on an IDLE GPU, same 100 dev paragraphs as llm_latency.py.

Refuses to time if the GPU already holds more than --max-busy-mib (another job would distort
the numbers). Batch-1 p50/p95 in ms after warm-up, and throughput at batch 32.
Writes results/latency_ours.json. Usage:
  ..\\torch_env\\Scripts\\python.exe code\\bench_latency.py results\\pilot\\T4_s0\\best.pt ...
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import torch
from transformers import AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data as D  # noqa: E402
import evaluate as V  # noqa: E402
from model import BACKBONE, JevPersuader  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ckpts", nargs="+", type=Path)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--max-busy-mib", type=int, default=3000)
    a = ap.parse_args()
    busy = V.gpu_busy()
    if busy and busy["memory_used_mib"] > a.max_busy_mib:
        raise SystemExit(f"GPU busy ({busy}); run when no other job holds the GPU")
    dev = D.load(D.DEV_ALL)
    texts = [r["paragraph_text"] for r in random.Random(0).sample(dev, a.n)]
    out_path = ROOT / "results" / "latency_ours.json"
    res = json.loads(out_path.read_text()) if out_path.exists() else {}
    for ck in a.ckpts:
        c = torch.load(ck, map_location="cpu", weights_only=False)
        cfg = c["config"]
        backbone = cfg.get("backbone", BACKBONE)
        model = JevPersuader(backbone=backbone, evidence=cfg["arm"] == "cea",
                             parser=cfg.get("parser", "none"))
        model.load_state_dict(c["model"])
        model.to("cuda").eval()
        tok = AutoTokenizer.from_pretrained(backbone)
        model.pad_id = tok.pad_token_id
        r = V.latency(model, tok, texts, torch.device("cuda"))
        r["gpu_busy_before"] = busy
        res[str(ck)] = r
        print(ck, r)
        del model
        torch.cuda.empty_cache()
    out_path.write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
