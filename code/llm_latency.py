"""Speed of Paper 1's generative route on the same GPU and dev paragraphs (run on an IDLE GPU).

Model: Qwen3-4B + Paper 1's grounded-SFT LoRA adapter
(../sftgrpo/finalsftgrpo/checkpoints/sft_qwen3_4b_r64/sft_final, loaded read-only), Paper 1's
inference prompt (copied to code/p1_copy/), thinking on, greedy, max_new_tokens 640 (Paper 1's
settings). To be fair to the LLM we time its FAST configuration (bf16 weights, KV cache on),
not the 4-bit/no-cache configuration Paper 1 used for evaluation.

Measures on N dev paragraphs (fixed seed): batch-1 latency p50/p95 (seconds) and generated
tokens, and batched throughput (paragraphs/s at batch 16, left padding). Writes
results/llm_latency.json. Our encoder's numbers come from evaluate.py / bench_latency.py on the
same paragraphs and GPU.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics as st
import sys
import time
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.dont_write_bytecode = True  # never write caches next to read-only sources
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "p1_copy"))
sys.path.insert(0, str(HERE))
from inference_prompt import render  # noqa: E402
import data as D  # noqa: E402

ROOT = HERE.parent
ADAPTER = ROOT.parent / "sftgrpo" / "finalsftgrpo" / "checkpoints" / "sft_qwen3_4b_r64" / "sft_final"
BASE = "Qwen/Qwen3-4B"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--max-new-tokens", type=int, default=640)
    ap.add_argument("--batch", type=int, default=16)
    a = ap.parse_args()
    dev = D.load(D.DEV_ALL)
    texts = [r["paragraph_text"] for r in random.Random(0).sample(dev, a.n)]
    tok = AutoTokenizer.from_pretrained(str(ADAPTER))
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"
    base = AutoModelForCausalLM.from_pretrained(BASE, dtype=torch.bfloat16, device_map="cuda")
    model = PeftModel.from_pretrained(base, str(ADAPTER)).merge_and_unload().eval()
    model.config.use_cache = True
    prompts = [tok.apply_chat_template([{"role": "user", "content": render(t)}], tokenize=False,
                                       add_generation_prompt=True, enable_thinking=True)
               for t in texts]

    @torch.no_grad()
    def gen(batch_prompts):
        enc = tok(batch_prompts, return_tensors="pt", padding=True).to("cuda")
        out = model.generate(**enc, max_new_tokens=a.max_new_tokens, do_sample=False,
                             pad_token_id=tok.pad_token_id)
        torch.cuda.synchronize()
        new = out[:, enc["input_ids"].shape[1]:]
        return [int((row != tok.pad_token_id).sum()) for row in new]

    gen(prompts[:2])  # warm-up
    lat, ntok = [], []
    for p in prompts:
        t0 = time.perf_counter()
        ntok += gen([p])
        lat.append(time.perf_counter() - t0)
    t0 = time.perf_counter()
    for s in range(0, len(prompts), a.batch):
        gen(prompts[s:s + a.batch])
    thr = len(prompts) / (time.perf_counter() - t0)
    res = {"model": f"{BASE} + {ADAPTER.relative_to(ROOT.parent)} (merged, bf16, KV cache)",
           "n": len(texts), "max_new_tokens": a.max_new_tokens,
           "p50_s": st.median(lat), "p95_s": sorted(lat)[int(0.95 * len(lat)) - 1],
           "mean_generated_tokens": st.mean(ntok), "hit_max_new_tokens": sum(n >= a.max_new_tokens for n in ntok),
           "throughput_para_per_s": thr, "batch": a.batch,
           "gpu": torch.cuda.get_device_name(0)}
    (ROOT / "results" / "llm_latency.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
