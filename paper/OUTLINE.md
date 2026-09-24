# Paper outline (draft 0, 2026-09-24; claims marked with their evidence and status)

Working title (owner to accept): Evidence-Safe System One: Fast, Calibrated, Span-Grounded
Persuasion Detection
Venue target: ACL family through ARR (owner default), or ArgMining / a SemEval workshop if the
full study shrinks the effects. No em-dashes anywhere in the prose.

## One-paragraph story

"System One" models such as Jev make fast, calibrated, typed decisions but never say why; open
reproductions confirm none outputs evidence. Generative LLMs can explain but are slow, and their
cited "evidence" is not guaranteed to be in the text. We build a 184M-parameter encoder that
detects 19 persuasion techniques and, in the same single pass, cites the exact spans that
support each decision with a calibrated probability. Two training ideas make the evidence
faithful: supervision of evidence spans, and counterfactual evidence manipulation (CEM), edits
of the gold evidence paired with matched control edits so the model cannot learn edit
artifacts. The two only help together. We also test a discourse parser as the evidence
proposer, motivated by the link between discourse units and persuasion spans: the link is
real, but the evidence-supervised encoder learns it on its own, so the parser can be dropped.

## Sections and the evidence each needs

1. Introduction: problem (fast and faithful, not either); contributions list (below).
2. Related work: System One models and open reproductions (notes/jev_ecosystem_2026-09-23.md);
   propaganda span tasks (SemEval-2020 T11, SemEval-2021 T6, WANLP 2022); faithful rationales
   (Lei 2016, FRESH, ERASER); counterfactual augmentation (CAD, RACE, MiCE); discourse and
   propaganda (Chernyavskiy et al. 2024; the owner's RST study); Paper 1 as the generative
   contrast. (LIT_REVIEW.md)
3. Model: JevPersuader (label head, learned span proposer, Brier-trained evidence scorer,
   consistency term); two prediction modes; why supervised proper scoring is the correct
   stand-in for RLCD here (notes/jev_mapping.md).
4. CEM v2: families, matched controls, boundary edits, fluency matching (AUC ~0.5), cue cap,
   definitional exclusion (Repetition), human audit and soft targets (notes/cem_v2_design.md,
   data/cem_v2_pool.meta.json, results/cem_audit/).
5. Evaluation protocol: official-style micro/macro F1; calibration (label, all-proposal and
   cited-span ECE, holdout-fitted); evidence hit and recall; artifact-balanced faithfulness with
   held-out families (RELOC, SUFF); comprehensiveness with matched control; selective
   prediction; idle-GPU latency; grounding rate.
6. Results: the 2x2 (evidence x CEM), 10 seeds [PENDING full study]; speed and grounding vs
   Paper 1's LLMs (results/llm_contrast.json, results/llm_latency.json [PENDING]); backbone
   choice (results/backbone/ [RUNNING]).
7. Discourse analysis: alignment table with chance control (results/discourse_alignment.json);
   the parser nulls (prior, candidates, oracle; STATUS 2026-09-24); the model cites EDU-aligned
   evidence on its own (results/cited_span_edu_alignment.json); probe (results/probe_edu.json).
8. Limitations: English only; one dataset; LLM contrast uses Paper 1's fine-tuned models; CEM
   label validity bounded by the audit; relocation sensitivity [check at 10 seeds].

## Contributions (keep only what the full study supports)

C1 An evidence-safe System One model: every decision cites exact input spans with calibrated
   probabilities, in one encoder pass. [supported at seed 0: grounding 1.000, cited-span ECE
   0.055 after Platt, p50 ~25 ms idle]
C2 (LEAD CANDIDATE) CEM v2, an artifact-balanced counterfactual augmentation with matched
   controls, fluency matching and human-audited labels, that makes a plain encoder more faithful
   at no accuracy cost and doubles as a faithfulness benchmark with held-out families.
   [3 seeds (results/seedcheck.md): SUFF (held out) +0.124 sd 0.024, KILL -0.056, INJECT
   +0.066, SWAP -0.044, all seeds significant; F1 +0.009 sd 0.006; RELOC +0.016 (limitation);
   audit PENDING; 10 seeds PENDING]
C3 A cautionary finding: the unbalanced v1 augmentation hurt the plain model and produced an
   apparent "synergy" with the evidence head that vanishes with the artifact-balanced v2; and
   train-pool strings in the inject test inflated it about threefold. Evaluation design, not
   the model, created those effects. [seed 0; supported by the v1 vs v2 tables]
   (RETRACTED earlier C3: "evidence supervision and CEM help only together".)
C3b Open tension: the evidence head, given CEM, lowers label faithfulness (SUFF 0.260 vs
   0.336); beta = 0 ablation QUEUED.
C4 Discourse finding: persuasion evidence aligns with discourse units (chance-controlled), and
   an evidence-supervised encoder learns this without a parser; explicit parsers add nothing at
   inference. [seed 0, several converging checks]

## Do not claim

- Higher detection accuracy than plain fine-tuning (seed 0: +0.012 [-0.007, +0.030], n.s.).
- A large no-hallucination advantage over fine-tuned LLMs (they cite verbatim 97-98%).
- That the parser helps; that RL is needed; Jev or Laya self-reported numbers.
