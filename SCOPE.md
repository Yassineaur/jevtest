# SCOPE

Working title: **Evidence-Safe System One: Fast, Calibrated, Span-Grounded Persuasion Detection**
(owner to accept; Stage 1.5).

## v2 as built (2026-09-23; where this section and the older text below disagree, this wins)

- One DeBERTa-v3-base pass (`code/model.py`, `JevPersuader`) gives: the label head p_t (CLS,
  19 sigmoids); a learned span proposer (per-technique start/end token scores, top-8 spans per
  technique up to 64 tokens: the "parser" that collaborates with the decision model, P1l); and an
  evidence scorer q_{t,s} on the proposed spans ([first; last; mean; width] -> MLP), trained with
  a plain Brier score so q is a calibrated probability that the span is gold evidence (token IoU
  >= 0.5).
- Loss: BCE(labels) + boundary BCE (proposer) + Brier(evidence) + 0.1 * (p_t - max_s q_{t,s})^2.
- Two prediction modes from the same pass: full-text p_t, and span-grounded max_s q_{t,s} (the
  label implied by the best evidence span). A FRESH-style re-encode of the cited spans alone
  (faithful by construction) is a planned third mode for the full study.
- Frozen-DMRST candidates (P1f) and exhaustive windows (P0) are ablations of the proposer, not
  yet built. RL (T2) stays parked: the open System One reproductions show proper scoring plus
  temperature, not RL, is what calibrates.
- Data: train 9,498 paragraphs (including 5,738 without a technique), cut by article into fit
  (8,550) and holdout (948) for selection and temperature; dev 3,127 paragraphs for reporting.

## Model

- **Encoder:** DeBERTa-v3-base (about 184M: 768 hidden, 12 layers, vocab 128,100), non-generative,
  locked 2026-09-23 so the T0
  control, our system, and the DeBERTa contrast share the exact backbone. (ModernBERT-large is
  a later option if we want to mirror Laya.)
- **Discourse parse:** DMRST parser, run once per article and cached. EDUs and relations are
  reused across the article's paragraphs. The parse provides (a) candidate span boundaries
  and (b) discourse features, both optional and ablated.
- **Inputs:** one paragraph (a physical line of the article) plus the article's cached parse.

## Heads (both non-generative)

- **Label head:** `p_t = P(technique t present)` for the 19 English techniques (multi-label).
- **Evidence head:** a calibrated span scorer. For each technique `t`, it assigns
  `q_{t,s} = P(span s is evidence for t)` to candidate sub-spans of the paragraph. The model
  predicts span boundaries (start and end token indices) inside the paragraph, so every cited
  span is an exact substring of the input. This is the structural no-hallucination guarantee.
  Multi-span per technique is supported (Paper 1's `data_io` already handles it).

## Candidate span sets (the parser ablation)

- **P0:** all token windows (no parser). The baseline grounding set.
- **P1f:** EDU-aligned windows from the FROZEN DMRST parser. The model may only start/end a
  span at EDU boundaries.
- **P1l (headline):** a LEARNED candidate-span proposer, jointly trained with the decision
  model. A small boundary scorer over token pairs proposes candidate spans and soft-selects
  the top ones; the evidence head then scores the selected (technique, span) pairs. Because
  the CEA loss backprops through the soft selection, the proposer learns to surface exactly
  the spans the evidence head finds load-bearing. This is the "parser collaborates with the
  Jev model" design: the parser's job is reframed from producing discourse structure to
  proposing the candidate evidence spans the decision model needs, and it co-adapts to that
  job.

P1l is a differentiable learned span-proposer, not a jointly trained full RST tree parser
(a discrete RST tree is not differentiable and would need its own supervision). This is the
tractable form of the joint-parser idea.

The parser ladder is P0 (none) vs P1f (frozen discourse) vs P1l (learned, co-trained). We test
whether P1l > P1f > P0 for evidence precision and calibration. Our prior from the RST feature
ablation is null, so we report the effect honestly; if P1l is not better than P0, the honest
story shrinks to "calibrated evidence-span attribution without a learned proposer."

## Operating modes

- **Span-grounded mode:** labels plus evidence spans plus calibrated confidence. The novel
  mode.
- **Full-text mode:** labels plus calibrated confidence only (evidence head disabled). The
  no-span ablation and the deployment fallback.

## Training: Calibrated Evidence Attribution (CEA)

```
L = S(y_t, p_t)                            proper scoring rule on labels (like Jev RLCD)
  + alpha  * S(z_{t,s}, q_{t,s})           proper scoring rule on evidence spans vs gold
  + beta   * ( p_t - A(q_{t,·}) )^2        label-evidence consistency
```

- `S` is a strictly proper scoring rule (Brier or log), used with the same class of
  positive-frequency weighting the RST paper already applies.
- `A` is an evidence-to-label aggregator (start with noisy-OR: `1 - prod_s (1 - q_{t,s})`).
- **Optional RL wrapper:** optimize the joint objective as a reward via policy gradient.
  This extends Jev's RLCD from a single scalar decision to a joint label-plus-evidence
  structured decision. Treated as an ablation, not a crutch (our RL nulls predict it may add
  little).

The genuinely new training content is the **evidence channel plus the consistency term**;
neither is present in Jev RLCD, conformal multi-label, or standard NER.

## Counterfactual Evidence Manipulation (CEM) augmentation (the faithfulness engine)

To make the label a faithful FUNCTION of the evidence (so the model actually uses the spans,
not paragraph priors), each (paragraph, technique t, gold evidence span s) yields a small set
of perturbed views with well-defined 19-dim label targets (the original, except for the
technique(s) the view manipulates). Implemented in `code/augment.py`.

- **V0 original:** unchanged. target t = 1 (anchor).
- **V1 evidence kill:** erase s. target t = 1 only if another t span remains, else 0.
  (Sensitivity: the label must drop when its evidence is removed.)
- **V2 distractor:** swap two words outside s. target t = 1. (Invariance to irrelevant change.)
- **V3 technique swap:** replace s with a cue of a DIFFERENT technique t' (a real gold span for
  t'). target t = 0 (if s was the only t span), t' = 1. (Technique specificity: the label must
  follow the evidence to the right technique.)
- **V4 relocation:** move s to another position. target t = 1. (Position invariance.)
- **V6 evidence inject:** insert a t cue (a real gold span for t) into a t-NEGATIVE paragraph.
  target t = 1. (Sensitivity: the label must appear when the evidence is added.)
- **V5 paraphrase (deferred):** rephrase s. target t = 1. The only view that needs text
  generation; when added it is audited against gold.

Most views are compositional over REAL gold spans (erase, swap, relocate, inject reuse actual
annotated spans), so the augmentation is cheap, scalable, and auditable (no LLM generation
except the deferred V5). The same counterfactuals are the FAITHFULNESS BENCHMARK at eval time:
kill the gold span (does p_t drop?), distractor (does p_t stay?), inject (does p_t rise?),
swap (does the label move to the right technique?). A plain encoder (no such training) and a
generative LLM (less faithful to specific spans) are the models we expect to beat on these.

So the full "new training method" is CEA (calibration + grounding) plus CEM (faithfulness via
counterfactual evidence manipulation).

## Evaluation (reuses Paper 1 infrastructure, copied into `code/`)

- **Quality:** micro and macro F1 per technique, official scorer. Must match or beat the
  label-only baselines so we do not trade quality for novelty.
- **Calibration:** expected calibration error (ECE) plus reliability diagrams, for labels AND
  for evidence spans, per technique with sample sizes.
- **No-hallucination:** grounding rate (expected near 100% by construction for P0/P1) plus
  evidence precision/recall against the dev span gold (1,801 spans), contrasted with a
  generative LLM baseline that can emit out-of-source spans.
- **Causal span load-bearing (from Paper 1):** comprehensiveness
  `p(t | full) - p(t | erase gold span)` recomputed on our non-generative model. If erasing a
  gold evidence span does not drop the calibrated label or evidence probability, the span was
  not load-bearing. This is a novel, reviewer-proof evaluation that directly reuses Paper 1's
  metric on the new system.
- **Speed:** p50 and p95 latency per paragraph, against the generative LLM baseline.

## Ablation ladder (10 seeds, paired bootstrap CIs on every delta)

- **Training:** T0 BCE labels only, T1 plus temperature scaling, T2 RLCD on labels only
  (the Jev control), T3 plus evidence-span head, T4 plus consistency term (full CEA).
- **Span source:** P0 token windows versus P1 EDU-aligned.
- **Generative versus non-generative:** our system against Paper 1's LLM route (the headline
  contrast for no-hallucination and speed).

Full cross: `{T0..T4} x {P0, P1}`, plus the generative contrast.

## Data

- **Span gold (read-only, do not edit):**
  - Train: 7,201 spans / 3,745 paragraphs / all 19 techniques
    (`../semeval/data/en/train_subtask3_spans.jsonl`).
  - Dev (held-out): 1,801 spans / 90 files
    (`../semeval/data/en/dev-labels-subtask-3-spans/`).
- **Copy policy:** any processed or derived data goes into `data/` inside this folder. We read
  the gold in place; we never write to it.
- **Per-technique skew (disclose):** Loaded_Language 2,447 spans down to
  Appeal_to_Popularity 15, Obfuscation 17, Whataboutism 18. Rare techniques have too few spans
  for stable per-technique ECE. Handle by reporting per-technique metrics with sample sizes
  and CIs, and by pooling the rare techniques into a "low-frequency" group for the calibration
  headline.

## In scope

- The non-generative encoder system, the CEA training, the evaluation battery, the ablations,
  and the generative-versus-non-generative contrast on the English split.

## Out of scope (for now)

- Multilingual (the span gold is English; other languages have span folders but no validated
  English-equivalent protocol yet).
- Re-annotation of spans (we use the existing gold; no new human annotation in the MVP).
- The Laya/Jev product itself (we reference it only as the motivation and as a baseline
  style, not as our contribution).
