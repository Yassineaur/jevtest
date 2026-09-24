# HANDOFF (read this first in a new session)

The resume point: intent, state, what is built and verified, what is next, how to run, and every
constraint. Reading order: this file -> `STATUS.md` (dated decision log, newest entries at the
bottom of "Dated decisions") -> `MVP_PLAN.md` (pre-registered kill criteria) -> `SCOPE.md`
(design; its "v2 as built" section wins over older text) -> `LIT_REVIEW.md` -> `IDEA.md`.
Research notes: `notes/jev_ecosystem_2026-09-23.md` (Jev and its ~35 open reproductions).

## What we are trying to do (the owner's ask, in their terms)

A Jev-like "System One" model for persuasion-technique detection that beats other models on
**speed, faithfulness, and (bonus) accuracy**, with novelty on several axes at once:

- **Fast:** one encoder pass, no autoregressive generation.
- **No hallucination:** every cited evidence span is a token range of the input (exact substring).
- **Points to the evidence** with **calibrated certainty** on both the label and the span.
- **Two prediction modes:** full-text (label head) and span-grounded (label implied by the best
  evidence span).
- **A parser that collaborates with the Jev-like model** by proposing candidate spans: built as
  the learned boundary proposer (P1l) jointly trained with the decision model.
- **A new training method** in the spirit of Jev's RL for calibrated decisions: SFT first with
  proper scoring (CEA objective); RL is parked as an ablation.
- **The owner's augmentation idea** (write one input several ways: change the evidence span and
  the label disappears, change another word and it stays, unchanged stays) plus extra variants:
  built as CEM in `code/augment.py` (V0 anchor, V1 kill, V2 distractor, V3 technique swap,
  V4 relocate, V6 inject; V5 paraphrase deferred). The same edits are the faithfulness test.
- **Controls and contrasts:** DeBERTa label-only model (T0) is the control; Paper 1's heavy
  LLMs are the contrast. Target: a paper with real, reviewer-proof contributions.

## Paper 1 (`../sftgrpo/`, READ-ONLY): context and contrast

Paper 1 (submitted ARR, #2363) fine-tuned generative LLMs (Qwen3-4B, Gemma, Llama; SFT then
DPO/GRPO) on the SAME SemEval-2023 span gold and the SAME 3,127 dev paragraphs.
- Context: its causal comprehensiveness idea `p(t|full) - p(t|erase span)` is reused (with a
  matched same-length control) in `code/evaluate.py`.
- Contrast, measured from its existing prediction files by `code/llm_contrast.py`:
  fine-tuned LLMs reach dev micro-F1 0.27-0.31 and cite verbatim 97-98% of their spans (so the
  no-hallucination gap vs fine-tuned LLMs is only about 2 points; vs base LLMs it is large).
  Paper 1's own DeBERTa baselines (label + per-token span head) reach 0.385-0.387: "DeBERTa + span
  head" is not new. Our delta must be calibrated span-level evidence, the label-evidence
  consistency coupling, CEM, and speed.

## State (2026-09-23, end of session 3)

Stage 3 (MVP go/no-go). The v2 system is built, CPU-verified and GPU-verified; the kill-switch
pilot (T4 vs T0, seed 0) was launched on the 5090. PILOT RESULTS: see the newest `STATUS.md`
entry and `results/pilot/`.

Built and verified:

| File | What | Verified by |
|---|---|---|
| `code/build_span_jsonl.py` | copy of the SemEval span builder | rebuilt `data/train_spans_all.jsonl` (9,498 paragraphs incl. 5,738 without a technique) and `data/dev_spans_all.jsonl` (3,127) with `--keep-empty-paragraphs` |
| `code/augment.py` | CEM views | `python code/augment.py --validate-all` -> bad_offsets=0 |
| `code/data.py` | cleaning (zero-width chars), article-level fit/holdout split, CEM epochs, tokenisation + char->token spans, batching | `..\torch_env\Scripts\python.exe code\data.py` -> cover_mismatch=0 on train and dev |
| `code/model.py` | JevPersuader v2: label head + learned span proposer (top-8 per technique, <=64 tokens) + Brier-trained evidence scorer; `evidence=False` = T0 | `code/cpu_test.py` -> SMOKE TEST PASSED |
| `code/train.py` | resumable SFT (checkpoint every 500 steps and each epoch, exact mid-epoch resume, DONE marker, holdout selection) | CPU + GPU smoke runs, rerun prints "already DONE" |
| `code/evaluate.py` | quality (both modes), label + evidence calibration (holdout temperature), evidence hit/recall, grounding rate, CEM faithfulness with matched controls, comprehensiveness with CI, latency | CPU run on a smoke checkpoint |
| `code/compare.py` | paired bootstrap T4 vs T0 (F1, kill-minus-control, invariances) | self-compare gives 0 on every contrast |
| `code/llm_contrast.py` | Paper 1 LLM grounding rates (read-only) | `results/llm_contrast.json` |
| `code/run_pilot.ps1` | resumable launcher: T4 then T0 | running/ran on the 5090 |

## How to run

```
cd C:\Users\SM GAMING\Documents\phd\jevpersuation
..\torch_env\Scripts\python.exe code\cpu_test.py                     # smoke test (CPU)
powershell -ExecutionPolicy Bypass -File code\run_pilot.ps1           # pilot (resumes; skips DONE arms)
..\torch_env\Scripts\python.exe code\evaluate.py --ckpt results\pilot\T4_s0\best.pt
..\torch_env\Scripts\python.exe code\evaluate.py --ckpt results\pilot\T0_s0\best.pt
..\torch_env\Scripts\python.exe code\compare.py results\pilot\T4_s0 results\pilot\T0_s0 --out results\pilot\compare_T4_vs_T0_s0
python code\llm_contrast.py
```

- `python` on PATH has no torch; use `..\torch_env\Scripts\python.exe` for anything with torch.
- GPU: 5090, about 12.5 it/s for T4 at batch 16 (about 2.4 min per epoch, 6 epochs max). Before a
  GPU run check `ninfer-status` (qwen may hold VRAM; `ninfer-stop` unloads it; if the session
  itself runs on qwen, do not stop it mid-session) and `nvidia-smi`.
- Disk: only 26 GB free on 2026-09-23. best.pt is 0.74 GB per run; last.pt (2.2 GB) is deleted at
  DONE. Budget before the 10-seed study (4 arms x 10 seeds x 0.74 GB = 30 GB will NOT fit:
  save bf16 weights or keep only heads + a seed subset).
- Smoke tests: pass `--device cpu` (an empty CUDA_VISIBLE_DEVICES does not hide the GPU on
  Windows).

## Bugs already found and fixed (do not re-introduce)

1. 12-token window cap (v1) made 21% of gold spans uncitable -> learned proposer up to 64 tokens.
2. Pos-weighted evidence Brier (v1) is NOT a proper score: it trains over-confident q -> plain
   Brier on the small proposal set (cpu_test checks the minimiser equals the base rate).
3. The shared train jsonl drops all technique-free paragraphs -> rebuilt with
   `--keep-empty-paragraphs`.
4. Spans cut by 512-token truncation were trained as half spans -> now dropped (location unknown).
5. PowerShell 5.1 `Tee-Object` writes UTF-16 logs -> launcher now appends UTF-8.

## Latest (2026-09-24, end of session 3) - read this first

All queued GPU work is DONE and every run is scored with EVAL_VERSION 2026-09-24f. Canonical
tables: `results/table_2x2_cemv2.md` (current), `results/table_2x2.md` (v1, historical),
`results/backbone_table.md`, `results/seedcheck.md`; speed `results/llm_latency.json` +
`results/latency_ours.json`. Decisions: backbone DeBERTa-v3-base lr 4e-5; parser dropped from
inference; lead contribution = CEM v2 (3-seed check passed). Waiting on the owner for the
human audit, disk space and full-study approval (STATUS.md "Next actions"). Nothing is running.

## Late session 3 state (read STATUS.md bottom entries for numbers)

- Pilot = GO. 2x2 (evidence head x CEM v1, seed 0) in `results/table_2x2.md` (built by
  `code/factorial.py`; refuses to mix evaluator versions, current EVAL_VERSION 2026-09-23c):
  T4+CEM 0.405 > T0 noCEM 0.393 > T4 noCEM 0.387 > T0+CEM 0.372. Evidence head helps only with
  CEM; CEM helps only with the evidence head (synergy). One seed only.
- Parser (owner's idea, grounded in Chernyavskiy 2024 + `results/discourse_alignment.json`):
  distilled DMRST segmenter head coupled to the span proposer by per-technique gates
  (`--parser prior`), control `--parser multitask`; eval-time prior modes oracle / shift / zero.
  Design: `notes/parser_design.md`. Arms T4seg_s0, T4disc_s0 in `results/parser/`.
- Augmentation v2 (owner asked for a concern-free augmentation): `notes/cem_v2_design.md`,
  `code/augment_v2.py`, frozen pool from `code/build_cem_v2.py` -> `data/cem_v2_pool.jsonl`
  (+ meta with SHA-256). Train with `--cem v2`; soft targets via `--soft-json` after the human
  audit. HUMAN AUDIT PENDING: `results/cem_audit/audit_sheet.csv` (v1 sample; regenerate for v2
  with a v2 sampler before scoring soft targets).
- Parser verdict (2026-09-24): all ways of feeding the parser in are null because the
  evidence model already cites discourse units on its own; parser dropped from inference, kept
  as an analysis instrument (STATUS.md).
- GPU chain (relaunched 2026-09-24 on the FINAL CEM v2 pool, SHA e546ca64; if it died, rerun
  the same two commands, everything resumes and skips DONE arms):
  `powershell -ExecutionPolicy Bypass -File code\run_arms.ps1 -Group cemv2 -Arms "T4v2_s0:cea:cem:0:--cem;v2,T0v2_s0:label:cem:0:--cem;v2"`
  then `-Group backbone -Arms "debB_lr4e5:cea:cem:0:--lr;4e-5,mbB_lr3e5:cea:cem:0:--backbone;answerdotai/ModernBERT-base;--lr;3e-5,mbB_lr6e5:cea:cem:0:--backbone;answerdotai/ModernBERT-base;--lr;6e-5,debL_lr1e5:cea:cem:0:--backbone;microsoft/deberta-v3-large;--lr;1e-5,debL_lr2e5:cea:cem:0:--backbone;microsoft/deberta-v3-large;--lr;2e-5"`
  (selection rule pre-registered in MVP_PLAN.md).
- UPDATE 2026-09-24 (supersedes the chain above): cemv2 T4v2/T0v2, debB_lr4e5 and both
  ModernBERT runs are DONE and evaluated (ModernBERT rejected, checkpoints deleted). The
  DeBERTa-large runs hit the VRAM cap at batch 16 and were restarted at batch 8 x grad-accum 2.
  Current queue (rerun these if the session died; finished arms are skipped):
  `powershell -ExecutionPolicy Bypass -File code\run_arms.ps1 -Group backbone -Arms "debL_lr1e5:cea:cem:0:--backbone;microsoft/deberta-v3-large;--lr;1e-5;--batch-size;8;--grad-accum;2,debL_lr2e5:cea:cem:0:--backbone;microsoft/deberta-v3-large;--lr;2e-5;--batch-size;8;--grad-accum;2"`
  `powershell -ExecutionPolicy Bypass -File code\run_arms.ps1 -Group cemv2 -Arms "T4v2b0_s0:cea:cem:0:--cem;v2;--beta;0"`
  then on an IDLE GPU: `..\torch_env\Scripts\python.exe code\bench_latency.py <best.pt files>` and
  `..\torch_env\Scripts\python.exe code\llm_latency.py`; then `code\backbone_table.py`,
  `code\factorial.py v1` and `code\factorial.py v2`.
- All runs so far were re-scored with EVAL_VERSION 2026-09-24e except the ones the queue is still
  producing (they get e automatically).
- Disk is tight (about 14 GB free): see the STATUS.md 2026-09-24 DISK entry.
- After the chain, on an IDLE GPU: `code/bench_latency.py <all best.pt>` and
  `code/llm_latency.py` (Paper 1 Qwen3-4B SFT at its fastest config) for the speed table.
- Known contamination fixed: dev INJECT edits now use dev-internal material (EVAL_VERSION c);
  latency inside evaluate.py is invalid when the GPU is shared (use bench_latency.py).

## What is next (in order)

1. Read the pilot: evaluate both arms, run compare.py, judge K1, K2, K4 against the numbers
   pre-registered in `MVP_PLAN.md`; record GO / NO-GO / PIVOT in `STATUS.md`. (DONE: GO.)
2. If GO: owner approval for the full study (10 seeds; arms T0, T4, T4-noCEM, T0-noCEM, plus
   the proposer ablations P0/P1f and the FRESH-style span-only re-encode mode); fix the disk
   budget first.
3. Read Meguellati et al. (ICWSM 2026) for their SemEval-2023 Subtask 3 numbers (accuracy/speed
   bar) and FRESH (span-only mode setup).
4. Measure the LLM latency contrast properly (Paper 1 did not log latency): time a Paper 1 SFT
   checkpoint on 200 dev paragraphs with the same GPU.
5. Working title in `SCOPE.md` awaits the owner's acceptance.

## Operating constraints (owner-set; keep them)

- All work stays inside `jevpersuation/`. Paper 1 (`sftgrpo/`) and the span gold
  (`semeval/data/en/`) are READ-ONLY; reuse = copy into `code/` or `data/`.
- Plain English; NO em-dashes in paper prose; expand acronyms once.
- Critical-reviewer mode; every headline number traces to a result file plus checkpoint.
- Thresholds and temperatures are fitted on the train holdout, never on dev.
- 10 seeds and paired bootstrap CIs for the full study; the pilot is one seed by design.
- Main-paper experiments need the owner's explicit approval; kill-switch pilots may run
  autonomously. Long jobs: resumable launcher, owner's terminal preferred.

## Do-not-claim

- "First model that outputs persuasion spans" (SemEval-2020 Task 11 did spans).
- A large no-hallucination advantage over fine-tuned LLMs (they are 97-98% verbatim).
- That the parser/proposer is the active ingredient before the P0/P1f ablations.
- That RL is necessary; Laya/Jev self-reported numbers.
