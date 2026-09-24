# Task-specific discourse parser coupled to the Jev-like model (design, 2026-09-23)

## Owner's idea

"Chernyavskiy, Ilvovsky & Nakov (EACL 2024) found a link between the parser and the techniques,
so we can have a custom parser for this task, coupled with a Jev-like model, forming an efficient
pipeline for fast inference with confidence and no hallucination."

## What the evidence says the parser should do

1. As a LABEL feature, discourse gives little over a strong baseline: Chernyavskiy +0.046 over
   a weak base (0.329); the owner's RST paper +0.014 (p = 0.12, 10 seeds) over 0.374-0.384, and
   its cross-batch probe showed the label models used only generic, not paragraph-specific,
   discourse information.
2. As an EVIDENCE UNIT, discourse is strongly paragraph-specific
   (`results/discourse_alignment.json`, DMRST, chance-controlled): a gold span is a whole run of
   EDUs 24% vs 5% by chance; argumentative techniques 64-80% vs 11-22%; lexical techniques
   (Loaded Language, Name Calling) sit inside EDUs (2-8%).

So the parser's job here: tell the evidence proposer WHERE argument units begin and end, with
a learned per-technique reliance, so argumentative techniques snap to discourse units and
lexical ones ignore them.

## Architecture (one encoder pass, no external parser at inference)

- **Segmenter head (the custom parser):** Linear(H, 2) on the shared encoder: per-token
  P(EDU starts here), P(EDU ends here). Trained by distillation from the owner's cached DMRST
  parses (silver labels) on the original (V0) paragraphs only; parser-fallback articles masked.
  Its output is DETACHED before use, so it stays a segmenter and cannot turn into a second
  technique detector.
- **Coupling (technique-gated boundary prior):**
  start_t(i) = s_t(i) + a_t * P_edu_start(i),   end_t(j) = e_t(j) + b_t * P_edu_end(j)
  with a_t, b_t learned per technique (initialised 0). After training, (a_t, b_t) are an
  interpretable readout of which techniques use discourse boundaries; they are checked against
  the chance-controlled alignment table (a pre-stated prediction: gates larger for Doubt,
  Causal Oversimplification, Appeal to Authority, False Dilemma than for Loaded Language and
  Name Calling).
- **Evidence scorer** also sees [P_edu_start(i), P_edu_end(j-1)] for each proposal.
- Cost: one Linear on hidden states. The external DMRST parser (an XLM-R encoder plus a
  decoder over the whole article) is never run at inference.

## Controls (one thing changes at a time)

| Arm | Segmenter loss | Prior / features used | Tests |
|---|---|---|---|
| T4 (done) | no | no | baseline evidence model |
| T4-seg | yes | no (gates fixed at 0) | multi-task representation effect alone |
| T4-disc | yes | yes | the coupled parser |
| eval: oracle | - | DMRST boundaries in place of predicted | distillation gap (upper bound) |
| eval: shifted | - | predicted prior rolled by a random offset | do POSITIONS matter (matched control) |
| eval: zeroed | - | prior set to 0 | how much the trained model leans on the prior |

Primary readouts: evidence top-1 hit and gold recall@3 overall and for the argumentative
techniques; micro-F1 (must not drop, K1 logic); latency.

## Backbone choice (to be measured, not assumed)

Pilot on the T4 recipe, one seed, same data and selection: DeBERTa-v3-base (184M; the
SemEval-2023 and Paper 1 standard, and the Chernyavskiy backbone), ModernBERT-base (149M; used
by the open Jev reproductions, faster attention, 8k context), DeBERTa-v3-large (435M; the
accuracy ceiling). Choose on dev micro-F1, evidence hit and latency together; a larger model
only if its gain exceeds the seed spread measured for the base model.
