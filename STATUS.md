# STATUS

## Stage

Stage 3 complete (MVP = GO on the mechanism; seed-0 pilots, ablations, backbone pilot and speed
contrast done). Waiting on the owner for: the human audit of the CEM v2 pool, disk space, and
approval of the 10-seed full study (MVP_PLAN.md). (as of 2026-09-24)

## Dated decisions

- 2026-09-23: Assessed `NandhaKishorM/laya` (open "System 1 decision engine") and Jev
  (TypeSafe AI's closed hosted counterpart). Verdict: a standard encoder classifier plus a
  structured head plus calibration; a useful tool/baseline, not a research contribution on its
  own.
- 2026-09-23: Ran the novelty check (arXiv API + Semantic Scholar). Provisionally novel on
  every axis the owner named. DAVinCI (2604.21193) confirmed as related work, not a collision.
- 2026-09-23: Confirmed the owner has real span-level technique gold (train 7,201 / dev 1,801
  spans, all 19 techniques), used in Paper 1, with reusable infrastructure in
  `sftgrpo/finalsftgrpo/src/`. This removed the main feasibility blocker.
- 2026-09-23: Owner set the operating constraint: all work stays inside `jevpersuation/`;
  Paper 1 and the shared span gold are read-only; reuse means copy, never edit in place.
- 2026-09-23: Adopted the design "grounded, calibrated, non-generative persuasion detection
  with evidence-span attribution" and the CEA training objective. See `SCOPE.md`.
- 2026-09-23: Locked design v2 with the owner: DeBERTa-v3-base backbone (the T0 control, our
  system, and the DeBERTa contrast share the exact encoder); SFT-first (supervised CEA, RL
  parked as the T2 ablation); a LEARNED candidate-span proposer (P1l) jointly trained with the
  decision model (the "parser collaborates with the Jev model" design); and the CEM
  counterfactual augmentation (V0 anchor, V1 kill, V2 distractor, V3 technique swap, V4
  relocate, V6 inject; V5 paraphrase deferred). See `SCOPE.md` / `IDEA.md`.
- 2026-09-23: Built and verified the CEM generator `code/augment.py`. Full-train self-check:
  90,226 views, 7,183 evidence-present, 0 bad span offsets. MVP v1 supervises the evidence head
  on evidence-present views (V0, V2) only; the evidence-manipulated views (V1, V3, V4, V6)
  train the label head. Data quirk: some gold paragraphs/spans contain zero-width spaces, so
  the tokenizer pipeline must strip/normalize them.
- 2026-09-23: Built the model `code/model.py` (DeBERTa-v3-base ~184M + 19-way label head +
  calibrated evidence head over P0 candidate windows) and the CEA loss; CPU-verified in
  `code/cpu_test.py` (forward shapes, finite loss, backward reaches both heads, T0 control
  finite). The review caught a real objective bug: the evidence Brier loss was too imbalanced,
  so the head could cheat to all-zeros; it is now a pos-weighted Brier, verified non-degenerate
  (the cheat costs 0.500, correct localization costs 0.000).
- 2026-09-23: Corrected the backbone size to ~184M (DeBERTa-v3-base: 768 hidden, 12 layers,
  vocab 128,100), not the 421M ModernBERT figure previously quoted.
- 2026-09-23: Second targeted arXiv pass (papers cross-check): the CEM and non-generative
  calibrated evidence-span attribution claims both survive. Added MultAttnAttrib (2026,
  training-free attention readout for long-doc QA) to `LIT_REVIEW.md` as the closest
  non-generative span-attribution neighbor; distinguished.

- 2026-09-23 (session 3, Opus): Third literature sweep (web + fast track/OpenAlex, which covers
  the ACL Anthology). Jev is closed and its "never hallucinates" means schema matching only; about
  35 open reproductions exist (Laya, OpenJev Verdict, open-jev, von, NanoJev...), none outputs
  evidence and none targets persuasion; in the open ones calibration comes from proper scoring plus
  temperature, not RL (Laya's RLCD checkpoints ship at ECE 0.466 before temperature). New
  neighbours: SemEval-2020 Task 11 / 2021 Task 6 / WANLP 2022 (span + technique tasks, so "outputs
  spans" is not new), FRESH / Lei 2016 (faithful-by-construction rationales), CAD / RACE,
  Meguellati et al. ICWSM 2026 (lightweight SemEval-2023 Subtask 3 model). Verdict: Partially
  novel. See `LIT_REVIEW.md` and `notes/jev_ecosystem_2026-09-23.md`.
- 2026-09-23: BUG (design): the v1 model's 12-token window cap made 21.0% of gold spans
  uncitable, concentrated in the argumentative techniques (Doubt median 19 tokens,
  Causal_Oversimplification 20, Appeal_to_Hypocrisy 22). Fixed in model v2 by the learned
  boundary proposer (spans up to 64 tokens = 99.3% of gold). This proposer IS the "parser that
  collaborates with the Jev model" (P1l).
- 2026-09-23: BUG (objective): the v1 pos-weighted evidence Brier moves the optimum to
  w*p/(w*p+1-p), so it trains over-confident evidence probabilities and contradicts the calibration
  claim. v2 uses the unweighted (proper) Brier on the small proposal set (about 2% positives, so no
  collapse). `cpu_test.py` now checks the Brier minimiser equals the base rate.
- 2026-09-23: BUG (data): the shared `train_subtask3_spans.jsonl` drops all paragraphs without a
  technique (3,760 kept of 9,498). Training on it would leave no negatives. Copied the builder to
  `code/build_span_jsonl.py` and rebuilt train (9,498) and dev (3,127) with
  `--keep-empty-paragraphs` into `data/`. Also: spans cut by 512-token truncation are dropped (not
  trained as half spans). Data self-check: 7,160 train / 1,771 dev spans mapped, 0 cover mismatches.
- 2026-09-23: Built `code/data.py`, `code/model.py` v2 (JevPersuader), `code/train.py`
  (resumable), `code/evaluate.py`, `code/compare.py`, `code/run_pilot.ps1`. Two prediction modes
  from one pass: full-text (label head) and span-grounded (max evidence probability).
- 2026-09-23: Pre-registered numeric kill criteria K1-K4 in `MVP_PLAN.md` BEFORE any dev number.
  Launched the pilot on the 5090 (T4 then T0, seed 0): 12.5 it/s, about 2.4 min per epoch.
  Disk is 26 GB free (not 75); last.pt is deleted when a run finishes.

- 2026-09-23: K3 input (no GPU), `code/llm_contrast.py` -> `results/llm_contrast.json`, from
  Paper 1's existing dev predictions (read-only): grounded-SFT/RL LLMs cite verbatim 97.3-98.3%
  of their spans (ungrounded after normalisation 0.9-2.2%); base LLMs 20-88% verbatim. So our
  structural 100% beats fine-tuned LLMs by only about 2 points. Consequence: no-hallucination is
  a supporting claim, not the headline; lead with accuracy + speed + calibrated evidence +
  causal faithfulness. Paper 1 LLMs also generate a median of about 1,400 characters per
  paragraph (reasoning + answer), which the encoder does not. Paper 1 already has a DeBERTa with
  a per-token span head (`evaluation/deberta_joint.py`, dev micro-F1 0.385; separate heads
  0.387): "DeBERTa + span head" is not new either; our delta vs it is calibrated span-level
  evidence, the consistency coupling and CEM.

- 2026-09-23: **PILOT VERDICT: GO (mechanism), seed 0, dev 3,127 paragraphs.** Files:
  `results/pilot/T4_s0/eval/metrics.json`, `results/pilot/T0_s0/eval/metrics.json`,
  `results/pilot/compare_T4_vs_T0_s0.json` (checkpoints `results/pilot/*/best.pt`).
  | Check (pre-registered in MVP_PLAN.md) | Result | Verdict |
  |---|---|---|
  | K1 quality | T4 0.405 vs T0 0.372 micro-F1; diff +0.033, 95% CI [+0.014, +0.050] (paired bootstrap over paragraphs, ONE seed) | pass; evidence supervision improves detection |
  | K2 calibration | evidence ECE (all proposals, holdout temperature) 0.006; label ECE temp T4 0.0087 vs T0 0.0090 | pass as registered |
  | K2 honest add-on | cited top-1 spans: mean q 0.58 vs hit rate 0.35, ECE 0.247 raw; Platt fitted on 619 holdout cited spans -> dev ECE 0.055 | the displayed confidence needs Platt; report both |
  | K3 | see LLM contrast entry above (fine-tuned LLMs 97-98% verbatim) | small delta, supporting claim only |
  | K4a | erase own top span: p drop 0.558 vs 0.013 same-length control; diff 95% CI [0.52, 0.57] | pass |
  | K4b | kill minus control: T4 -0.237 vs T0 -0.213; diff -0.024 [-0.039, -0.009] | pass, small |
  | Evidence | top-1 hit 0.583, gold recall@3 0.683, grounding 1.000 | - |
  | Speed | T4 p50 21 ms / 1,627 paragraphs/s (bs 32); T0 17 ms / 1,796 | proposer costs about 10% |
  Surprise (pre-registered): T0 trained on the same CEM views is almost as evidence-sensitive
  as T4, so CEM may carry most of the faithfulness. Launched the no-CEM arms (T4nc, T0nc) to
  test it. References for scale: Paper 1 DeBERTa 0.385-0.387, Paper 1 LLMs 0.27-0.31, same dev.
- 2026-09-23: Owner pointed to Chernyavskiy, Ilvovsky & Nakov (EACL 2024): read in full
  (`_lit/chernyavskiy2024_discourse_propaganda_eacl.pdf`). Label gain 0.329 -> 0.375 from RST
  relation features, but on a weak baseline (the RST paper's 10-seed baseline is about 0.374-0.384
  and its discourse gain was +0.014, p = 0.12). Their Table 6 shows argumentative techniques'
  spans align with EDUs. Replicated with the owner's DMRST cache plus a CHANCE control
  (`code/discourse_align.py` -> `results/discourse_alignment.json`, 514 articles, 8,458 spans):
  span is a whole run of EDUs 24% vs 5% chance overall; Doubt 72% vs 22%, Causal
  Oversimplification 65% vs 11%, Straw Man 80% vs 13%; Loaded Language 8% vs 1.4%. Decision:
  the parser's role in this project is the EVIDENCE BOUNDARY PRIOR (per-technique learned
  weight), not a label feature. Design in `notes/parser_design.md`.

- 2026-09-23: No-CEM arms (seed 0, V0 views only): T4nc dev micro-F1 0.387 (span mode 0.410,
  top-1 evidence hit 0.551, comprehensiveness diff 0.562), T0nc done. Early reading: kill
  sensitivity exists without CEM (T4nc kill -0.182 vs T4 -0.203, T0 -0.183), while inject
  sensitivity rises sharply with CEM (0.108 -> 0.373) on exactly the family CEM trains, so
  it may be an edit artifact. Full 2x2 after re-evaluation with the final evaluator.
- 2026-09-23: Owner asked whether I wrote the augmented samples: no; every view is a
  rule-based edit of human gold spans. But a first audit sample (`results/cem_audit/`,
  `code/cem_audit.py`, 150 rows awaiting a human annotator) shows v1 edits are often
  ungrammatical and v1 had no matched control edits in training, so a model could learn
  "edited text = technique"; label rules were unaudited; train and test used the same edit
  families. Owner asked for the best solution: CEM v2 (`notes/cem_v2_design.md`,
  `code/augment_v2.py`, `code/build_cem_v2.py`): exact single-splice edits at sentence/EDU
  boundaries; each evidence edit paired with a same-kind, same-shape non-evidence control
  (artifact-balanced); edits may touch exactly one gold span; cue reuse capped at 5; GPT-2
  fluency filter (tau 0.30 nats/token) applied at the PAIR level; frozen hashed pool from the
  train-fit split; soft targets from the human audit once done; faithfulness judged on
  held-out families (RELOC, SUFF) as edit-minus-control with bootstrap CIs, trained families
  flagged. v1 kept frozen for reproducibility. v2 validation: 0 offset mismatches (exact
  string equality) on 35k views.
- 2026-09-23: Added matched controls to the v1 evaluation too (inject_ctrl: same-length
  non-evidence insertion) and the v2 faithfulness block (`faithfulness_v2` in evaluate.py,
  `faith_v2_pairs.jsonl`, paired in compare.py). All runs are re-evaluated with the final
  evaluator before any table.
- 2026-09-23: LESSON: running GPT-2 fluency scoring (batch 32 x 512 x 50k-vocab logits in
  fp32) beside a training run pushed the 5090 to 31.9 / 32.6 GB and cut training from 12.5 to
  1 it/s (Windows spills VRAM to RAM). Stopped it; fluency scoring now runs on the CPU. Rule:
  one heavy GPU job at a time; side jobs on CPU or small batches, checked with nvidia-smi.

- 2026-09-23: **CORRECTION to the pilot reading** (canonical table `results/table_2x2.md`,
  EVAL_VERSION 2026-09-23c, seed 0). (1) The dev INJECT test had used train-pool strings that the
  CEM models had seen inserted: re-run with dev-internal material, the T4+CEM INJECT effect fell
  from 0.343 to 0.130 (about two thirds was string memorisation). (2) The +0.033 F1 of T4 over
  T0 was against T0+CEM, a control that CEM itself weakens (T0: 0.393 -> 0.372). Against plain
  fine-tuning (T0 noCEM) the full system is +0.012 [-0.007, +0.030]: NOT significant.
  Corrected headline: at no accuracy cost, the full system is more faithful than plain
  fine-tuning on every artifact-balanced family except relocation: KILL -0.044 [-0.064,
  -0.025], INJECT +0.070 [+0.063, +0.076], SWAP -0.052 [-0.073, -0.030], held-out SUFF +0.066
  [+0.045, +0.086]; held-out RELOC +0.029 [+0.014, +0.044] is in the UNFAITHFUL direction (more
  position-sensitive). Interaction: the evidence head helps only with CEM and CEM helps only
  with the evidence head (F1 and SUFF). Superseded: the "K1 +0.033" line above is valid only as
  "T4 vs T0 under CEM"; do not quote it as a gain over plain fine-tuning.

- 2026-09-23: **Parser results (seed 0).** (1) The distilled segmenter works: one linear head
  on the shared encoder reproduces DMRST EDU boundaries at boundary F1 0.909 on dev
  (T4seg; 0.906 in T4disc), at no measurable latency cost (idle-GPU p50: T4 26.2 ms, T4seg
  25.3, T4disc 24.9; `results/latency_ours.json`). (2) The COUPLED prior FAILED its pre-stated
  test: learned gates all ~0 (-0.003 to -0.033); Spearman(gate, alignment excess) 0.18,
  one-sided permutation p = 0.23 (`results/gate_analysis.json`); replacing the prior by true DMRST
  boundaries, shifting it or zeroing it gives identical results (F1 0.395, recall@3 0.712).
  (3) Mechanism: EDU boundaries are already largely linearly decodable from encoders that never
  saw a parser (probe boundary F1 0.738 pretrained DeBERTa, 0.705 T4; `results/probe_edu.json`),
  so a prior computed from the same hidden states adds nothing the span proposer cannot learn
  from gold spans. (4) Full-text F1: T4seg 0.363, T4disc 0.395 vs T4 0.405 (one seed; seed
  spread unknown). Next: structural EDU-run candidates at inference (oracle DMRST vs own
  segmenter), running.

- 2026-09-24: Parser, continued. Structural candidates (runs of 1-3 EDUs added at inference,
  oracle DMRST or own segmenter) do NOT help: T4 argumentative top-1 hit 0.580 -> 0.578 with
  oracle EDUs, lexical 0.590 -> 0.561. Explanation, measured
  (`results/cited_span_edu_alignment.json`): T4, trained with NO parser, cites argumentative
  evidence that is a whole run of EDUs 67.6% of the time (gold 57.2%, same-length chance
  30.1%) and lexical evidence 4.3% (gold 6.4%, chance 1.3%). The span-supervised encoder has
  internalised the discourse-evidence link the Chernyavskiy paper and our alignment table show;
  an explicit parser adds nothing at inference (prior, features, candidates, oracle: all null).
  Decision: drop the parser from the inference pipeline (keeps it fast); keep the parser as the
  analysis instrument that shows what the model learned. Paper framing: "the link is real, and
  evidence supervision learns it without a parser".
- 2026-09-24: CEM v2 pool finalised. Built 26,115 candidate pairs -> 25,822 unique -> 15,142
  after the cue-reuse cap -> 5,923 after the pair-level GPT-2 fluency filter (tau 0.30). The
  filter left a residual fluency artifact (evidence KILL/SWAP edits more fluent than controls:
  AUC 0.366 / 0.380), removed by fluency MATCHING (|dNLL edit - dNLL control| <= 0.10): AUC
  KILL 0.450, INJECT 0.501, SWAP 0.467 -> 3,079 pairs. Then dropped 179 pairs whose inserted
  technique was Repetition (definitional: one inserted occurrence cannot be Repetition; also
  excluded from dev INJECT tests) -> FINAL 2,900 pairs, SHA-256 e546ca64f2ae...
  (`data/cem_v2_pool.meta.json`; unmatched copy kept). SWAP tech2 recovered from each pair's
  control for pairs built before it was recorded (287/287). Human audit sheet regenerated from
  the final pool: `results/cem_audit/audit_v2_sheet.csv` (165 rows; 40 per evidence family,
  15 per control family). EVAL_VERSION bumped to 2026-09-24e (all runs re-scored at the end).
- 2026-09-24: DISK: 11 GB free at one point (HF downloads + checkpoints); freed 3.5 GB of my
  scratch smoke checkpoints -> 14 GB. train.py now skips the resume checkpoint (with a warning)
  when free space < 12 bytes/param + 2 GB. The DeBERTa-v3-large backbone runs need ~7 GB each
  transiently. OWNER DECISION NEEDED before the 10-seed study: free space elsewhere (e.g. the
  RST paper's 127 GB of checkpoints under outputs/, ctrpaper 49 GB, graphwork 35 GB) or keep
  only selected checkpoints.

- 2026-09-24: **CEM v2 2x2 (seed 0, EVAL_VERSION e; canonical `results/table_2x2_cemv2.md`;
  v1 table rebuilt under version e in `results/table_2x2.md`).** Pivot of the claims:
  (a) CEM v2 on the PLAIN model (T0+CEMv2 vs T0): F1 +0.004 [n.s.]; faithfulness on every
  family: KILL -0.053 [-0.068, -0.038], INJECT +0.061 [+0.055, +0.068], SWAP -0.029 [-0.049,
  -0.009], held-out SUFF +0.097 [+0.081, +0.115], held-out RELOC +0.006 [n.s.]. The owner's
  augmentation idea, in its artifact-balanced form, is the faithfulness engine.
  (b) RETRACTED: the v1 "synergy" (evidence head helps only with CEM). With v1, CEM hurt the
  plain model (0.393 -> 0.372) because of noisy views; with v2 it does not (0.397), and the
  evidence effect given CEM is +0.004 [n.s.].
  (c) The evidence head provides citing ability (T4+CEMv2: span-mode F1 0.414, recall@3
  0.714, top-1 hit 0.559, cited-span ECE raw 0.111 vs 0.247 with v1, Platt 0.082) at no
  accuracy cost, but given CEM it REDUCES label faithfulness (KILL +0.044, SUFF -0.077 vs
  T0+CEMv2). Hypothesis: the consistency term ties p_t to the proposal scores. Next ablation:
  T4+CEMv2 with beta = 0.
  (d) Full system vs plain fine-tuning: F1 +0.009 [n.s.]; INJECT +0.029, SUFF +0.021 (held
  out), RELOC +0.022 (unfaithful direction), KILL and SWAP n.s.

- 2026-09-24: Backbone pilot, base models (`results/backbone_table.md`, rule pre-registered):
  DeBERTa-v3-base holdout 0.508 (lr 2e-5) / 0.524 (lr 4e-5), dev 0.405 / 0.394; ModernBERT-base
  holdout 0.493 / 0.496, dev 0.337 / 0.348: ModernBERT is clearly worse on this task (outside
  the 0.01 speed-preference margin) and is rejected. Holdout and dev disagree on DeBERTa-base's
  lr (single seed, 948-paragraph holdout), a reason for 10 seeds. Disk guard fired on the
  first DeBERTa-large run (6.0 GB free: resume checkpoint skipped, run continues). Deleted the
  two rejected ModernBERT best.pt files (1.2 GB); their config/log/metrics/preds are kept
  (`results/backbone/CHECKPOINTS_DELETED.txt`).

- 2026-09-24: LESSON: DeBERTa-v3-large + span proposer at batch 16 reached 32.1 / 32.6 GB
  VRAM (the machine's crash zone) and slowed to 1.3-2.1 it/s from spilling. Stopped it, deleted
  the partial run (it had not finished an eligible comparison), added `--grad-accum` to
  train.py (identical update when 1), relaunched both large runs at batch 8 x 2 (same effective
  batch 16). Rule: watch nvidia-smi in the first window of any new model size.

- 2026-09-24: Per-technique CEM v2 effect on the plain model (T0+CEMv2 vs T0, seed 0,
  `results/cemv2_per_technique_T0v2_vs_T0.json`): the faithfulness gain is concentrated in
  lexical/emotive techniques (SUFF +0.11 to +0.19: Loaded Language, Name Calling,
  Exaggeration, Flag Waving; INJECT up to +0.32 for Flag Waving); argumentative techniques
  small (Doubt SUFF +0.012) and rare ones ~0 (Whataboutism, Red Herring, Straw Man,
  Hypocrisy, Popularity: INJECT 0.000-0.002). Likely a floor effect (the model rarely
  predicts those, so p stays ~0 whatever the edit). Paper must report per-technique detection
  next to per-technique faithfulness; do not claim faithfulness for rare techniques.

- 2026-09-24: **Backbone decided** (`results/backbone_table.md`, pre-registered rule):
  DeBERTa-v3-base at lr 4e-5 (holdout 0.524). DeBERTa-v3-large ties on holdout (0.524 at lr
  2e-5) but is 2x slower (p50 34.9 vs 18.5 ms, 704 vs 1,280 paragraphs/s) and gains nothing on
  dev (best 0.405 = base's best); ModernBERT-base clearly worse (dev 0.337-0.348). Rejected
  large checkpoints deleted (metrics kept). Large runs used batch 8 x grad-accum 2.
- 2026-09-24: **Speed vs Paper 1's LLM measured** (same RTX 5090, same 100 dev paragraphs,
  idle GPU; `results/llm_latency.json`, `results/latency_ours.json`): Qwen3-4B + Paper 1's
  grounded-SFT adapter at its FAST configuration (merged bf16, KV cache, greedy, thinking on):
  p50 12.09 s per paragraph (mean 288 generated tokens), 1.01 paragraphs/s at batch 16.
  JevPersuader T4 + CEM v2: p50 18.5 ms at batch 1, 1,298 paragraphs/s at batch 32. About
  650x lower latency and 1,300x higher throughput.
- 2026-09-24: Two NEGATIVE ablations on why the evidence head lowers label faithfulness under
  CEM v2 (T4v2 SUFF 0.260 vs T0v2 0.336): (1) beta = 0 (no consistency term): SUFF 0.257, no
  recovery, and F1 -0.015 [-0.026, -0.004] (the term helps accuracy; keep it); (2) the
  span-grounded channel is not more faithful (T4v2 span-mode SUFF 0.211, RELOC 0.077). Cause
  unknown; test at 10 seeds before interpreting (it may be partly seed noise).
  EVAL_VERSION 2026-09-24f adds span-channel faithfulness (`faith_v2_span_pairs.jsonl`).

- 2026-09-24: **SEED CHECK PASSED for the headline** (`results/seedcheck.md`, code
  `code/seedcheck.py`; seeds 0-2, plain model with vs without CEM v2, same config as seed 0,
  EVAL_VERSION f; seed 1-2 checkpoints deleted after evaluation, metrics/preds kept):
  SUFF (held out) +0.124 (sd 0.024; seeds +0.097, +0.130, +0.144), KILL -0.056 (sd 0.008),
  INJECT +0.066 (sd 0.005), SWAP -0.044 (sd 0.014): every seed's paired 95% CI excludes 0 in
  the same direction. micro-F1 +0.009 (sd 0.006, never negative; plain-model seed spread
  0.370-0.393). RELOC +0.016 (sd 0.008; 2 of 3 seeds significant): a small increase in
  position sensitivity, to be reported as a limitation. This justifies asking for the full
  study.

## Safe claims (defensible today)

All seed 0 unless stated; each needs the 10-seed study before it goes into a paper.
- Speed: one encoder pass, p50 18.5 ms per paragraph and 1,298 paragraphs/s on an RTX 5090,
  about 650x faster than Paper 1's fine-tuned Qwen3-4B at its fastest configuration (12.09 s).
  (measured, not seed-dependent)
- Grounding: every cited span is an exact substring (1.000); fine-tuned LLMs 97-98% verbatim.
- Accuracy: the evidence model matches plain fine-tuning (+0.009, n.s.); DeBERTa-v3-base is the
  measured best backbone for speed and quality.
- CEM v2 makes a plain encoder more faithful on artifact-balanced tests at no accuracy cost,
  replicated over 3 seeds: held-out sufficiency +0.124 (sd 0.024), KILL -0.056, INJECT +0.066,
  SWAP -0.044, every seed significant; F1 +0.009 (sd 0.006). Caveat: RELOC +0.016 (slightly
  more position-sensitive). Gains concentrate in the techniques the model detects.
- Evidence citing: recall@3 0.714, top-1 hit 0.559, cited-span ECE 0.111 raw (0.082 after a
  holdout Platt fit).
- Discourse: persuasion evidence aligns with EDUs far above chance (argumentative 64-80% vs
  11-22%); the evidence model learns this without a parser (cited argumentative spans 67.6%
  EDU-aligned vs 30.1% chance); explicit parsers add nothing at inference.
- Supervised proper scoring is the correct stand-in for RLCD with full labels
  (notes/jev_mapping.md).

## Do-not-claim

- Higher accuracy than plain fine-tuning; the retracted v1 "synergy"; any INJECT number from
  before EVAL_VERSION c (train-string contamination).
- That the parser helps (prior, candidates, oracle: all null) or that the coupled gates learned
  the discourse link (p = 0.23).
- That the evidence head improves label faithfulness (it lowers it under CEM v2; cause open).
- Faithfulness for rare techniques (floor effect); a large no-hallucination advantage over
  fine-tuned LLMs; RL necessity; Jev/Laya self-reported numbers.

## Lessons

- Do not conclude "no span gold exists" from the paragraph-level RST pipeline; the span gold
  lives in `*-labels-subtask-3-spans/` and was used in Paper 1. Check the raw annotation
  folders before making feasibility claims.
- WebSearch was unavailable in-session; the novelty check leaned on the arXiv API and
  Semantic Scholar, which can miss ACL-Anthology-only workshop papers. Close that gap.
- The per-technique span counts are heavily skewed (2,447 down to 15); plan the calibration
  reporting and pooling accordingly.

## Next actions

(Items 1-6 of the 2026-09-23 list are DONE: data pipeline, model v2, training, evaluation,
learned proposer, LLM contrast, pilot, ACL/SemEval sweep.)
1. OWNER: annotate `results/cem_audit/audit_v2_sheet.csv` (README there), then
   `code/cem_audit.py --v2 --score` -> soft targets.
2. OWNER: free disk (about 11 GB free; the full study needs about 30 GB, or approve the
   keep-only-seed-0-checkpoints plan) and approve the full study in MVP_PLAN.md.
3. Full study: 4 arms x 10 seeds on DeBERTa-v3-base lr 4e-5 (backbone rule), CEM v2 with soft
   targets; hierarchical bootstrap; H1-H3 as pre-registered.
4. Then Stage 5 (paper): paper/OUTLINE.md; read Meguellati et al. 2026 and FRESH in full first.
