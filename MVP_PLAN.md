# MVP PLAN (kill-switch pilot)

## Full study proposal (DRAFT, needs the owner's approval; written 2026-09-24)

Launch only after: the backbone pilot picks a backbone, the CEM v2 seed-0 arms are read, and
the human audit of the v2 pool gives soft targets.
- Arms (2x2, the design the pilot showed matters): T0 plain fine-tuning (no CEM), T4 evidence
  head (no CEM), T0 + CEM v2, T4 + CEM v2 (soft targets). The parser is not in the main study
  (null at inference, see STATUS 2026-09-24); it stays an analysis section.
- 10 seeds per arm = 40 runs at about 12-15 min each on the 5090 (about 9 GPU-hours).
- Primary, pre-registered hypotheses (hierarchical bootstrap over seeds, then paragraphs or
  edit pairs; Holm correction across the three):
  H1 non-inferiority of detection: micro-F1(T4+CEMv2) - micro-F1(T0) > -0.01.
  H2 faithfulness on HELD-OUT families: SUFF(T4+CEMv2) > SUFF(T0), and
     RELOC(T4+CEMv2) not worse than RELOC(T0) by more than 0.02.
  H3 calibrated evidence: cited-span ECE after holdout Platt <= 0.05.
- Secondary: the 2x2 interaction, evidence top-1 hit and recall@3, label ECE, selective
  prediction (AURC), latency vs Paper 1's LLM, per-technique results.
- Disk: 40 x 0.74 GB = 30 GB does not fit (14 GB free). Proposal: keep best.pt for seed 0 of
  each arm; for seeds 1-9 keep config, logs, metrics and predictions and delete best.pt after
  evaluation (each number stays traceable to its eval files and reproducible from config and
  seed). Alternative: the owner frees space in older projects first.

## Backbone pilot pre-registration (written 2026-09-23, before any backbone run)

Recipe: T4 (evidence model, parser none, CEM v1 so it matches the pilot), seed 0, batch 16,
same data, split and schedule. Each backbone gets two learning rates around its published
recipe; the better one is chosen on the TRAIN HOLDOUT micro-F1 (never dev):
| Backbone | Params | LR grid |
|---|---|---|
| microsoft/deberta-v3-base | 184M | 2e-5 (pilot run), 4e-5 |
| answerdotai/ModernBERT-base | 149M | 3e-5, 6e-5 |
| microsoft/deberta-v3-large | 434M | 1e-5, 2e-5 |
Decision rule: take the backbone with the best holdout micro-F1 unless a smaller/faster one is
within 0.01 of it, in which case take the faster one (the project's claim is speed + quality).
A large model must beat the best base model on dev by more than the base model's seed spread
(measured in the full study) before it is claimed to be better. Report dev F1, evidence top-1
hit, p50 latency and throughput for all six runs.

## v2 pre-registration (written 2026-09-23, BEFORE any dev number was computed)

The pilot that actually runs is the v2 design (see STATUS.md, 2026-09-23 entries): T4 = CEA with
the learned span proposer (spans up to 64 tokens) + unweighted Brier evidence scorer +
consistency; T0 = same encoder and label head, label-only loss. Both arms train on the SAME CEM
view mix, seed 0, selection on the article-level train holdout, dev scored once by
`code/evaluate.py`. Paired comparisons by `code/compare.py` (paired bootstrap over dev
paragraphs, 2,000 resamples).

| Id | Question | Kill if | Metric source |
|---|---|---|---|
| K1 quality | does evidence cost detection? | 95% CI of (T4 - T0) dev micro-F1 lies entirely below -0.02 | compare.py |
| K2 calibration | is the evidence probability trustworthy? | T4 evidence ECE after holdout temperature > 0.05, OR T4 label ECE (temp) worse than T0 label ECE (temp, = the T1 baseline) by > 0.01 | metrics.json |
| K3 no-hallucination vs LLM | does the grounding delta exist? | PENDING: needs the generative contrast (Paper 1 route); not judged in this pilot | - |
| K4 faithfulness | do cited spans drive the label? | T4 comprehensiveness diff (own top span minus same-length control) has a 95% CI touching 0, OR T4's (kill - kill_ctrl) drop is not larger than T0's | metrics.json, compare.py |

What would surprise us: T0 (label-only, same CEM views) showing the same kill sensitivity as T4.
That would mean CEM alone, not the evidence channel, produces the faithfulness.

Budget: about 15 min per arm on the 5090 (measured 12.5 it/s, 1,794 steps per epoch, 6 epochs
max). Disk: best.pt 0.74 GB per arm; last.pt (2.2 GB) deleted at DONE. 26 GB free on 2026-09-23.

Goal: decide, cheaply and early, whether the core claim survives contact with our own
baseline, before any long run. This is a kill-switch pilot: it may run autonomously; record
the kill criterion before launching.

## What to build (the smallest system that tests the claim)

1. Copy the needed Paper 1 span code into `code/` (do not edit the originals):
   `config.py`, `data_io.py`, `span_faithfulness.py`, `rewards.py`, `output_parser.py`,
   `leak_detect.py`.
2. Build a data loader that yields, per paragraph: the text, the 19 label targets, the gold
   evidence spans (text and technique), and the candidate span set (P0 token windows, and
   P1 EDU-aligned windows from the cached parse).
3. Two configs on the SAME backbone (DeBERTa-v3-base), SFT-first (no RL in the pilot), both
   using the CEM counterfactual augmentation:
   - **T4 / P1l:** full CEA (label head + evidence head + consistency) + CEM, learned
     candidate-span proposer.
   - **T0 / P0:** the matched control (label-only BCE + CEM, no evidence head), token windows.
   (Frozen-discourse P1f and the RL wrapper T2 are ablations, run after the pilot if needed.)
4. A generative contrast: reuse Paper 1's LLM inference path (read-only) to produce
   techniques plus cited spans on the same dev paragraphs, so we can measure its grounding
   rate and latency against ours.

## Slice and budget

- Train on the full train split (7,201 spans) for a small number of epochs (the model is
  about 184M; a 5090 32GB handles it comfortably). One seed for the pilot, not ten.
- Evaluate on the full dev split (1,801 spans).
- Expected wall time: a few hours per config. Check free disk and VRAM before launching
  (75 GB free as of 2026-09-13; the 184M checkpoints are small).

## What to measure

- Micro and macro F1 per technique (official scorer) for T4/P1 versus T0/P0.
- Label ECE and evidence ECE for T4/P1 versus T0/P0.
- Grounding rate and evidence precision/recall for T4/P1, and for the generative LLM baseline.
- Causal comprehensiveness (`p(t|full) - p(t|erase gold span)`) for T4/P1.
- p50/p95 latency for T4/P1 versus the generative LLM baseline.

## Kill criteria (stop if any hold)

- **K1 (quality):** T4/P1 micro-F1 is below T0/P0 by more than the paired bootstrap CI.
  (We must not trade detection quality for the novelty.)
- **K2 (calibration):** T4/P1 evidence ECE is not better than T1 (label + temperature) on the
  same slices. (If post-hoc temperature already gives the calibration, the CEA evidence head
  is not earning its keep.)
- **K3 (no-hallucination):** our grounding rate is statistically indistinguishable from the
  generative LLM's grounding rate. (If the LLM is already near-perfectly grounded, the
  no-hallucination delta disappears.)
- **K4 (parser):** P1 evidence precision is not better than P0 beyond the CI AND the
  consistency term adds nothing. (Then the parser coupling and CEA are decorative, and the
  honest story shrinks to "calibrated label+evidence without the parser".)

## If it survives

- Go to the full 10-seed cross (`{T0..T4} x {P0, P1}`) with paired bootstrap CIs, then write
  the paper. If it survives but K4 holds, lead with "calibrated evidence-span attribution"
  and report the parser as a neutral/negative result.

## If it is killed

- Record which criterion fired and the mechanism. A controlled null with the ablation ladder
  is still publishable at the workshop tier (ArgMining / SemEval workshop), consistent with
  the RST paper's outcome.

## Guardrails

- 10 seeds and paired bootstrap CIs on every headline delta in the full study (pilot is 1
  seed by design).
- One canonical table per experiment in `results/`; superseded numbers struck through with a
  pointer.
- No writing outside this folder. All code and derived data stay in `jevpersuation/`.
