# Jev and the open "System One" ecosystem (research note, 2026-09-23)

Purpose: know exactly what Jev and its open reproductions do, so our contribution is stated
against them precisely. Sources are repo READMEs and vendor pages (self-reported; not peer
reviewed). Quote numbers only as "repo-reported".

## Jev (TypeSafe AI, closed, hosted)

- Source: typesafe.ai/blog/introducing-system-one-models-and-jev (fetched 2026-09-23).
- What it is: a non-autoregressive "System One" model. Input = unstructured state plus a
  schema of allowed outputs; output = typed decisions (classify, route, score, extract,
  branch) with probabilities and confidence, all in one parallel pass.
- Training: "Reinforcement Learning for Calibrated Decisions (RLCD)". No reward formula, no
  architecture, no size, no data are published.
- "Never hallucinates" means ONLY schema matching: "Schema matching is guaranteed, thus we can
  confidently add 0% into the plots." It is type-safety, not content grounding.
- Explanations, rationales, evidence, attribution: none.
- Speed claims: 70 to 500 ms end-to-end; "40x to 200x faster" than frontier models.

**The gap Jev leaves open (our opening):** Jev is type-safe but not evidence-safe. It
guarantees the output is a legal label, never that the label is supported by anything in the
input. Our model adds evidence-safety: each decision comes with the exact input spans that
support it, and a calibrated probability that those spans are the evidence.

## Open reproductions (GitHub, all 2026)

| Project | Backbone | Output heads | Training objective | Evidence spans? |
|---|---|---|---|---|
| Laya (NandhaKishorM/laya) | 421M encoder (mmBERT family) | noul / choice / score, labels written into the input | "RLCD": proper-scoring-rule rewards with GRPO-style policy gradient, then per-type temperature fitting | No |
| OpenJev Verdict (Heman10x-NGU/Verdict-open-jev) | ModernBERT-base 151M, GLiClass-style label-in-input | choice / score / noul + explicit `__insufficient_evidence__` abstain slot | Supervised CE + 1.0 * Brier (not RL) + post-hoc temperature | No |
| open-jev typed decision engine (intikhab49) | ModernBERT-base 150M, one Linear(d,1) at `<<l>>` marker per label | noul / choice / score | Soft CE + Brier on annotator distributions (no RL) | No |
| von (wfzyx/von) | not checked in depth | discrete / probabilistic / ordinal | not checked | No |
| NanoJev, nanojev, kev (Qwen2.5-0.5B LoRA), AnyJev / Simple Jev (read logits of any LLM), QwenJev (vision) | various | typed decisions | various | No |

Curated lists checked: MorrisZJ/awesome-open-system-one, madewithjev.com/open-source-jev
(about 35 entries). Independent evals: AbdelStark/jev-benchmarks, ickma2311/jev-baselines-eval
(Banking77, CLINC150), 4esv/jev-eval.

Findings that matter for us:

1. **No open reproduction outputs evidence, spans, or rationales.** Both curated lists and
   every README checked confirm it.
2. **None targets persuasion, propaganda, or misinformation.** Tasks are intents (Banking77,
   CLINC150), AG News, BoolQ, sentiment, prompt-injection, game control.
3. **RL is not what makes them calibrated.** Laya's RLCD checkpoints ship over-confident: mean
   ECE 0.466 before temperature, 0.081 after refitting one temperature per (type, option
   count) on held-out data (Laya README, "Calibration"). The two best-calibrated reproductions
   use plain supervised CE + Brier plus temperature, no RL. This supports our SFT-first choice
   and makes the T1 (label + temperature) baseline mandatory (kill criterion K2).
4. **Useful design ideas to borrow (optional ablations, not core):**
   - Label-in-input marker head (schema as data): lets rare techniques borrow from their
     written definitions. Candidate fix for the 15-span Appeal_to_Popularity tail.
   - Explicit abstention: our consistency term already ties label confidence to the best
     evidence span (no evidence, no confident label), which is a learned version of the
     `__insufficient_evidence__` slot.
5. **Known failure modes of the family we should test on ours:** label-word bias (Laya
   `noul` follows "true/false" option words), option-order sensitivity (Verdict flips 4.5% of
   choices under permutation), abstention collapse under paraphrase. Our CEM V2 (distractor)
   and V4 (relocation) views are direct tests of the analogous input-side brittleness.

## Consequence for the paper's claim

Honest positioning: "System One models (Jev and ~35 open reproductions) give fast, typed,
calibrated decisions but no evidence. We add evidence-safety: a fast encoder whose every
persuasion decision cites exact input spans with calibrated evidence probabilities, trained
with counterfactual evidence manipulation so the cited spans are causally load-bearing."
Jev itself is closed and cannot be run on our data without an API key; Laya (Apache-2.0) is
the runnable System One baseline if we want one in the table.
