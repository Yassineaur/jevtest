"""Generative-LLM contrast from Paper 1's existing dev predictions (read-only, no GPU).

For each Paper 1 run (preds_dev.jsonl under ../sftgrpo/finalsftgrpo/results/<run>/), measures
how often the LLM's cited evidence spans are grounded in the input paragraph:
  exact      the cited span is a verbatim substring of the paragraph
  normalized verbatim after lower-casing and collapsing whitespace and quote styles
  ungrounded not found even after normalisation (a fabricated or paraphrased "quote")
It also reports the parse failure rate and the length of the generated output (characters of
the raw generation, including any <think> block): the per-paragraph generation our encoder
does not have to produce. Latency itself was not logged by Paper 1, so it is not claimed here.

Our model cites token ranges of the input, so its exact-grounding rate is 1.0 by construction
(checked per run by evaluate.py as grounding_rate).

Writes results/llm_contrast.json. Nothing is written outside this project.
"""
from __future__ import annotations

import json
import re
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P1 = ROOT.parent / "sftgrpo" / "finalsftgrpo" / "results"
RUNS = ["qwen3_4b_baseline", "sft_qwen3_4b_r64", "sft_qwen3_4b_r32", "dpo_faith", "grpo_rare",
        "sft_llama31_8b", "llama31_8b_baseline", "sft_gemma2_2b", "gemma2_baseline",
        "mistral_baseline"]
QUOTES = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'",
                        "–": "-", "—": "-"})


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.translate(QUOTES)).strip().lower()


def main() -> None:
    out = {}
    for run in RUNS:
        f = P1 / run / "preds_dev.jsonl"
        if not f.exists():
            continue
        recs = [json.loads(l) for l in f.open(encoding="utf-8") if l.strip()]
        n_sp = exact = normed = 0
        raw_len = []
        unparse = 0
        for r in recs:
            text = r.get("text", "")
            unparse += int(not r.get("parseable", True))
            raw_len.append(len(r.get("raw", "") or ""))
            for s in r.get("pred_spans", []) or []:
                if not isinstance(s, str) or not s.strip():
                    continue
                n_sp += 1
                if s in text:
                    exact += 1
                    normed += 1
                elif norm(s) in norm(text):
                    normed += 1
        m = json.loads((P1 / run / "metrics_dev.json").read_text())
        out[run] = {
            "n_paragraphs": len(recs), "micro_f1": m["label_micro"][2],
            "n_cited_spans": n_sp,
            "exact_grounding": exact / max(1, n_sp),
            "normalized_grounding": normed / max(1, n_sp),
            "ungrounded_rate": 1 - normed / max(1, n_sp),
            "unparseable_rate": unparse / max(1, len(recs)),
            "median_generated_chars": st.median(raw_len) if raw_len else 0,
            "source": str(f.relative_to(ROOT.parent)),
        }
    (ROOT / "results" / "llm_contrast.json").write_text(json.dumps(out, indent=2))
    print(f"{'run':24s} {'F1':>6s} {'spans':>6s} {'exact':>6s} {'norm':>6s} {'unparse':>7s} {'gen chars':>9s}")
    for k, v in out.items():
        print(f"{k:24s} {v['micro_f1']:6.3f} {v['n_cited_spans']:6d} {v['exact_grounding']:6.3f} "
              f"{v['normalized_grounding']:6.3f} {v['unparseable_rate']:7.3f} {v['median_generated_chars']:9.0f}")


if __name__ == "__main__":
    main()
