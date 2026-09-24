# IDEA

## The one-paragraph concept

A fast, non-generative model that detects the 19 English persuasion techniques (SemEval-2023
Task 3) AND points to the evidence spans that support each technique, with **calibrated**
confidence on both the label and the span. It does not generate text, so it cannot
hallucinate an explanation or an out-of-source quote: it predicts span boundaries inside the
paragraph, so every cited span is a real substring of the input. It is an encoder (about
184M parameters), so it runs in a few tens of milliseconds, not seconds.

## Why this is the gap

Three existing families each miss one thing we need:

- **Encoder multi-label classifiers** (our own RST paper, every SemEval-2023 Task 3
  submission): fast and non-generative, but they output only labels. No evidence spans, no
  calibrated certainty, nothing to point an analyst at.
- **Generative LLMs with citations** (Paper 1's route, and the DAVinCI-style pipelines):
  can point at evidence, but they generate text, so they are slow and can hallucinate spans
  or quotes that are not in the source, and their confidence is uncalibrated.
- **Conformal / calibrated multi-label methods**: give calibrated label sets, but no spans
  and no evidence attribution.

No family delivers all four at once: **fast + no-hallucination + points to evidence +
calibrated certainty**. That combination is the contribution.

## The novelty map (verified 2026-09-23 via arXiv API + Semantic Scholar)

| Axis | Closest prior work | Status |
|---|---|---|
| Calibrated persuasion detection | KInITVeraAI at SemEval-2023 Task 3 (2023): per-language threshold tuning only, no calibration procedure | Novel |
| Calibrated **evidence-span** attribution | DAVinCI (2604.21193, 2026): calibration + evidence-span selection, but for **LLM claim verification** (FEVER), retrieval + entailment, generative. Not multi-label persuasion, not a grounded classifier | Novel (distinct, see LIT_REVIEW) |
| Calibrated multi-label (no spans) | Inductive conformal, "Well-calibrated Confidence Measures for Multi-label Text Classification" (2023) | Taken: mandatory baseline |
| Parser-coupled (discourse spans as evidence units) | RST used only as features (2015, 2019, RACE 2026) | Novel |
| New training (calibrated joint label+evidence) | "How Proper Scoring Rules Shape LLM Forecasting" (2026): single outcome only | Novel |

Two further novelty components locked 2026-09-23:

- **Learned joint candidate-span proposer (P1l).** Instead of a frozen discourse parser, a
  small boundary scorer is trained jointly with the decision model so it proposes exactly the
  candidate evidence spans the model needs (the "parser collaborates with the Jev model"
  design). Ladder: P0 (no proposer) vs P1f (frozen DMRST) vs P1l (learned, co-trained).
- **Counterfactual Evidence Manipulation (CEM) augmentation.** Each (paragraph, technique,
  gold span) yields perturbed views (kill the span, distractor, swap to another technique's
  cue, relocate, inject into a negative) with defined label targets, training the model to
  make its labels a faithful function of the evidence. The same counterfactuals are the
  faithfulness benchmark at eval time. This is the component most likely to beat a plain
  encoder and a generative LLM on faithfulness while keeping encoder speed.

Open gap still to close: a sweep of the ACL Anthology and SemEval workshop papers (arXiv
misses many of them) for any span-level or calibrated persuasion-technique detection.

## The Paper 1 to jevpersuation arc (the narrative)

Paper 1 asked, for a generative LLM that writes techniques plus cited spans, "does the cited
span actually drive the label?" Its answer is a causal measure: comprehensiveness
`p(t | full) - p(t | erase span)`. Paper 1's findings: RL optimizes F1, not faithfulness.

jevpersuation takes the **same span gold** and the **same "span drives the label" idea** and
removes the generator:

- Paper 1: generate span text, then test it causally. Slow, can hallucinate, uncalibrated.
- jevpersuation: predict calibrated span boundaries directly. Fast, grounded by construction,
  calibrated. The Paper 1 causal measure becomes one of our evaluation tools (does erasing a
  gold evidence span drop the calibrated label/evidence probability?).

So the two papers are a controlled contrast on the same data: generative-and-causal versus
non-generative-and-calibrated. That contrast is what lets us claim the no-hallucination and
speed deltas with a matched comparison, not a marketing claim.

## What makes it defensible (reviewer-proof)

- Matched controls for every treatment (our standard): the ablation ladder in `SCOPE.md`
  isolates exactly what each new ingredient buys (evidence head, consistency, RL, parser).
- The "no hallucination" claim is measured, not asserted: grounding rate plus evidence
  precision/recall against the dev span gold, contrasted with a generative LLM baseline that
  can emit out-of-source spans.
- Every headline delta carries a paired bootstrap CI over 10 seeds.
- The calibration claim is reported per technique with sample sizes, so the rare-technique
  skew is disclosed, not hidden.

## Do-not-claim (until proven)

- Do not claim the discourse parser is the active ingredient. Our RST feature ablation was
  null (+0.014 micro-F1, p=0.12). The parser's role here is as a source of candidate span
  boundaries, which is a different and untested claim.
- Do not claim RL is necessary. Our RL nulls say it likely is not; treat it as an ablation.
- Do not cite Laya/Jev benchmark numbers (self-reported; their Jev comparison uses vendor
  figures). We benchmark against our own matched baselines.
