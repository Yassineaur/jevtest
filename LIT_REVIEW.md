# LIT_REVIEW (closest neighbors, with distinctions)

Each entry states what it does and the specific way it is NOT our contribution. Verified
2026-09-23 via the arXiv API and Semantic Scholar (WebSearch was unavailable in-session); a
second targeted arXiv pass (2026-09-23) re-checked the CEM and non-generative span-attribution
claims and added MultAttnAttrib as the closest non-generative span-attribution neighbor.

Status: Partially novel. Taken: joint span plus technique detection (SemEval-2020 Task 11,
SemEval-2021 Task 6, WANLP 2022), fast calibrated non-generative decisions (Jev and about 35
open reproductions), faithful-by-construction rationales (Lei 2016, FRESH 2020) and
counterfactual augmentation (CAD, RACE). Left: a fast encoder whose multi-label persuasion
decisions cite exact spans with CALIBRATED evidence probabilities tied to the label by a
consistency term, trained with gold-span-anchored counterfactual evidence manipulation (CEM)
and audited causally against a generative LLM. Verdict updated 2026-09-23 after the third
sweep (web + fast track / OpenAlex, which covers the ACL Anthology).

| Nearest neighbour | What it already has | Our delta |
|---|---|---|
| SemEval-2020 Task 11 SI+TC systems | span identification + technique classification | spans as calibrated evidence for a paragraph decision; consistency term; CEM faithfulness training and test; speed vs LLM |
| Jev + open reproductions (Laya, OpenJev Verdict, open-jev) | fast, typed, calibrated decisions | evidence-safety (cited spans), persuasion domain, causal faithfulness |
| FRESH / Lei 2016 (select-then-predict) | faithful extractive rationales by construction | multi-label, calibrated span probabilities, gold-span supervision, both full-text and span-only modes |
| CAD / RACE / MiCE | counterfactual edits for robustness or explanation | deterministic, gold-span-anchored views with defined label targets, no generator, doubles as the faithfulness benchmark |
| Meguellati et al. ICWSM 2026 | lightweight SOTA on SemEval-2023 Subtask 3 | evidence, calibration, faithfulness (they report labels only); they are our accuracy/speed bar |
| DAVinCI, MultAttnAttrib | calibrated attribution (claims / QA) | task, learned vs training-free, multi-label persuasion |

## Added in the third sweep (2026-09-23)

### Span-level propaganda tasks (the "spans are not new" warning)
- **SemEval-2020 Task 11** (Da San Martino et al.): Span Identification (find propaganda
  fragments) and Technique Classification (label a given fragment), 14 techniques, news.
  Winning systems: transformer ensembles (Hitachi). **SemEval-2021 Task 6** subtask 2
  (spans + techniques in memes) and **WANLP 2022** subtask 2 (Arabic tweets, techniques with
  exact spans) do the same. So "a persuasion model that outputs spans" is NOT a contribution.
  What those systems lack: calibration of span probabilities, a coupling between the span and
  the paragraph decision, and any causal test that the span drives the decision. That is the
  part we claim.
- **Meguellati et al., ICWSM 2026**, "Towards Detecting Persuasion on Social Media"
  (arXiv 2503.13844, read 2026-09-24): XLNet-base (110M) trained on 211 French documents
  machine-translated to English; English Subtask 3 TEST micro-F1 0.4062, macro 0.2178 (vs
  KInIT 0.4038 / 0.1586, APatt 0.3756 / 0.1292); threshold fixed at 0.5; one run; 136 s per
  epoch; no evidence spans, no calibration. Not directly comparable to our DEV numbers (our
  data has no public test gold, only the template). Use: their number shows the accuracy
  ceiling of single small encoders is about 0.40 micro-F1, where our model also sits; our
  contribution is evidence + faithfulness + calibration at that accuracy, not accuracy.

### Faithful rationales
- **Lei, Barzilay, Jaakkola 2016** (rationalizing neural predictions) and **FRESH** (Jain,
  Wiegreffe, Pinter, Wallace, ACL 2020): extract a snippet, then classify from the snippet
  only, so the rationale is faithful by construction. Reviewer 2 will ask why our full-text
  CLS label head is not simply this. Answer in design: we run BOTH modes (full-text label
  head, and a span-only "evidence bottleneck" head that predicts from the selected spans), and
  report the accuracy cost of faithfulness-by-construction versus faithfulness-by-training.
- **SelfExplain** (EMNLP 2021), **UNIREX** (2022): self-explaining classifiers with phrase
  concepts or learned rationale extractors. Single-label, uncalibrated.
- **Zhou et al., AAAI 2022**, "Do feature attribution methods correctly attribute features?":
  builds ground-truth attribution by dataset modification. Close in spirit to CEM as an
  EVALUATION; CEM also uses it as TRAINING and uses real gold spans instead of planted ones.

### Counterfactual augmentation
- **Kaushik et al. 2020 (CAD)**, **RACE** (EMNLP 2023, rationale-sensitive counterfactual
  augmentation for fact verification), **MiCE** (2021, minimal contrastive edits). All use
  humans or a generator to write label-flipping edits. CEM differs: edits are deterministic
  operations on gold evidence spans (delete, relocate, swap technique, inject a real span from
  another paragraph, distract with non-span edits), each with a defined label target, so every
  view is auditable against gold with no generator in the loop (V5 paraphrase is the only
  generative view and is deferred).

### System One models
- Jev and the open reproductions are summarised in `notes/jev_ecosystem_2026-09-23.md`. Main
  point: none outputs evidence, none targets persuasion, and in the open ones calibration comes
  from proper scoring plus temperature, not from RL.

## The two that could have killed the claim

### DAVinCI (arXiv 2604.21193, 2026)
"Trust but Verify: Introducing DAVinCI, a Framework for Dual Attribution and Verification in
Claim Inference for Language Models" (Rawte, Rossi, Dernoncourt, Lipka).
- What it does: a two-stage framework for **LLM claim verification** on FEVER and
  CLIMATE-FEVER. Stage (i) attributes a generated claim to internal model components and
  external sources; stage (ii) verifies each claim with entailment-based reasoning and
  confidence calibration. Ablations isolate evidence-span selection, recalibration thresholds,
  and retrieval quality.
- Why it is NOT a collision:
  1. Task: fact-checking generated claims, not detecting persuasion techniques in a document.
  2. "Attribution" means claim provenance (model / source), not pointing to in-text spans that
     evidence a label.
  3. It is generative-LLM plus retrieval plus entailment, the opposite of a non-generative
     grounded classifier.
  4. It calibrates claim-verification confidence; we calibrate both label and evidence-span
     probabilities with a consistency constraint, and we have a no-hallucination grounding
     guarantee by construction.
- How we use it: cite as the closest calibrated-evidence work; distinguish on task,
  non-generativity, and multi-label persuasion.

### Inductive conformal multi-label (2023)
"Well-calibrated Confidence Measures for Multi-label Text Classification with a Large Number
of Labels."
- What it does: set-valued, calibrated multi-label document classification with coverage
  guarantees.
- Why it is NOT a collision: no spans, no evidence attribution, no non-generative grounding
  story.
- How we use it: it is a **mandatory baseline** for the calibration axis. Our claim must be
  "calibrated label-plus-evidence", not merely "calibrated labels".

## Related, different task or setting

- **MultAttnAttrib (Tran et al., 2026):** training-free long-document (unimodal + multimodal) QA
  attribution. It reads selected PREFILL attention heads and applies calibrated thresholds to
  locate evidence spans in a document, with per-span confidence. Closest neighbor to the
  non-generative span-attribution axis (found 2026-09-23, 2nd arXiv pass). NOT a collision:
  (1) TRAINING-FREE (a frozen model's attention readout) vs our LEARNED span scorer q_{t,s}
  trained with CEA + CEM; (2) spans locate QA answers, not multi-label persuasion-technique
  classification; (3) attention-derived, not a learned boundary objective with a label-evidence
  consistency constraint; (4) no CEM faithfulness training. Cite as the closest non-generative
  span-attribution work; distinguish on learned-vs-training-free, multi-label classification,
  and the consistency/CEM training.
- **KInITVeraAI at SemEval-2023 Task 3 (2023):** multilingual fine-tuning for persuasion
  detection; adjusts confidence thresholds per language. No calibration procedure, no ECE,
  no spans. Shows the task, not the calibration or attribution angle.
- **"Beyond Final-Token Classification: Heterogeneous Readouts for Evidence-Grounded Suicide
  Risk Detection" (2026):** combines risk/factor outputs with verbatim phrase candidates under
  calibrated, risk-conditional constraints. Nearest in spirit (calibrated evidence grounding)
  but a different task (suicide risk), single-domain, and not multi-label persuasion.
- **"Bag of Tricks or Bag of Myths ... Suicide Risk Assessment" (2026):** produces evidence
  spans and applies deployment-consistent calibration to factor values. Different task.
- **TTPrint (2026):** multilabel technique extraction (cybersecurity TTPs) anchored to source
  windows by span localization. Closest on "multilabel + spans" but a different domain, and no
  calibration or grounding guarantee.
- **AILS-NTUA at SemEval-2026 Task 8 (2026):** RAG conversation evaluation coupling evidence
  span extraction with calibrated multi-judge selection. Retrieval-based, not a classifier.

## Discourse / RST as features (not as evidence units)

- "Better Document-level Sentiment Analysis from RST Discourse Parsing" (2015): composes local
  information up the discourse tree.
- "Improved Document Modelling with a Neural Discourse Parser" (2019): neural discourse
  representations for summarization.
- RACE (2026): RST logic graph plus EDU-level features for LLM-generated text detection.
- None uses discourse spans as the **attribution/evidence units a classifier points to**.
  Ours does (the P1 candidate set). Note our own RST feature ablation was null, so this is
  the riskiest novelty axis.

## Training-side neighbors

- **"How Proper Scoring Rules Shape LLM Forecasting" (2026):** uses proper scoring rules as
  training rewards for single-outcome LLM event forecasting. Closest to the RLCD-style idea;
  no spans, no joint label-plus-evidence structured output, no consistency term.
- Standard NER / span classification: one span one label, no calibration, no multi-label
  evidence attribution.
- Attention-based explainability: not discrete spans, not calibrated, not checkable against
  gold. Our discrete span head with calibration and a grounding guarantee is structurally
  different.

## The motivation (not the contribution)

- **Jev (TypeSafe AI) and Laya (github.com/NandhaKishorM/laya):** the "System 1 decision
  engine" and its RLCD (RL against strictly proper scoring rules) calibration. We reference
  these as the motivation for fast, calibrated, non-generative decisions, and as a baseline
  style. We do not adopt their self-reported benchmark numbers. Laya is Apache 2.0 and could
  serve as an off-the-shelf baseline to contrast against.

## Open gap (status)

- ACL Anthology / SemEval sweep: DONE 2026-09-23 via fast track (OpenAlex indexes the
  Anthology). It found the SemEval-2020/2021/WANLP span tasks and Meguellati et al. (ICWSM
  2026); none calibrates spans or tests them causally. No calibrated persuasion-detection
  paper found.
- Still to read in full before writing: Meguellati et al. 2026 (their exact Subtask 3 numbers
  and model size) and FRESH (for the span-only mode's setup).
