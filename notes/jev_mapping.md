# Is this a correct "Jev-like" model? Property-by-property mapping (2026-09-23)

Jev's published properties (typesafe.ai launch post; see notes/jev_ecosystem_2026-09-23.md) and
how JevPersuader implements and verifies each.

| Jev property | JevPersuader implementation | How it is verified |
|---|---|---|
| Non-autoregressive: one parallel pass, no token generation | one encoder pass produces all 19 decisions, the proposals and their scores | latency on an idle GPU (`code/bench_latency.py`) vs Paper 1's LLM at its fastest config (`code/llm_latency.py`) |
| Typed outputs from a fixed schema ("never makes type errors") | outputs are fixed fields: 19 probabilities and, per technique, (start, end) token indices with a probability; an index pair cannot be malformed | by construction; grounding rate = 1.000 checked in every evaluation |
| Calibrated probabilities | labels: BCE (the log score, strictly proper); evidence: Brier (strictly proper); one holdout temperature for labels, Platt on holdout cited spans for displayed evidence | label ECE, evidence ECE, cited-span ECE on dev, all fitted on the train holdout only |
| Confidence used to gate decisions | label probability tied to the best evidence probability by the consistency term; both exposed | selective-prediction curves (risk vs coverage) to add |
| RLCD training | supervised proper scoring (see below); RL kept as the T2 ablation | T2 ablation if needed |
| Small, fast backbone | DeBERTa-v3-base (184M) by default; ModernBERT-base and DeBERTa-v3-large in the pre-registered backbone pilot | `results/backbone/`, rule in MVP_PLAN.md |

What JevPersuader adds that Jev does not have: evidence-safety (every decision cites exact input
spans with a calibrated probability), a task-specific discourse parser coupled to the evidence
proposer, and counterfactual training plus artifact-balanced faithfulness tests.

## Why supervised proper scoring, not RL, is the correct "RLCD" here

RLCD rewards a model with a strictly proper scoring rule (for example the log or Brier score of
the outcome). For a one-step decision whose correct answer is known for every training item,
the expected reward is maximised by exactly the probabilities that minimise the same proper
score in supervised training; the policy gradient is an unbiased but higher-variance Monte-Carlo
estimate of the supervised gradient (it sees only the sampled action's reward, bandit feedback,
instead of the full label vector). RL earns its keep only when the reward is available but the
label is not (outcome feedback, delayed or non-decomposable rewards). SemEval-2023 gives full
labels and gold spans, so supervised proper scoring is the lower-variance estimator of the same
optimum. The open reproductions agree empirically: Laya's RL-trained checkpoints ship with
mean ECE 0.466 until a temperature is refitted, while supervised CE+Brier reproductions are the
best calibrated (notes/jev_ecosystem_2026-09-23.md). The paper should state this argument
explicitly; the T2 RL ablation is optional confirmation, not a missing piece.

## Known deviations to disclose

- Jev reads a schema at inference (labels as data); JevPersuader has fixed heads for the 19
  techniques. For a fixed taxonomy this is the standard, faster design; label-in-input is an
  optional extension for unseen techniques.
- Jev's exact architecture is unpublished, so "Jev-like" means the published properties above,
  not a replication.
