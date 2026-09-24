# v3 design: zero-shot techniques and unseen languages (DRAFT, 2026-09-24)

Status: design only, nothing built or run. Needs the owner's answers (bottom) and approval before
any main-paper run. Novelty context: `notes/novelty_v3_2026-09-24.md`.

## Goal in one paragraph

Jev's strength is that the output schema is data: you hand it new labels and it decides without
retraining. v3 brings that to persuasion detection at span level, on two axes at once:
(1) **unseen techniques**: a technique never seen in training is detected, with evidence spans,
from its written definition alone; (2) **unseen languages**: a model trained with English labels
works in a language it never saw labels (or translations) for, because training aligns the
languages in one shared space. Both rest on the same mechanism: spans and technique definitions
are compared in a shared vector space, so anything that lands in the right place in that space
(a new definition, a sentence in a new language) works without new labels.

## Architecture (one encoder pass, as before)

1. **Multilingual backbone** (required for unseen languages; the current DeBERTa-v3-base is
   English-only). Backbone pilot with a pre-registered rule, as in MVP_PLAN.md:
   mDeBERTa-v3-base (about 278M, mostly the embedding table, so compute close to the current
   model), XLM-R-base, XLM-R-large. Must also report the English cost vs the current T4 (dev
   micro-F1 0.40).
2. **Suspicion proposer (A):** technique-agnostic start/end scores, top-K spans (K about 16),
   trained on the union of all gold spans.
3. **Definition encoder (C):** each technique's written definition (from the SemEval-2023
   annotation guidelines) is encoded ONCE by the same encoder and cached as a vector d_t.
   Unseen technique = add a new definition vector; no retraining.
4. **Judge:** q_{s,t} = sigmoid(<W h_s, d_t> / tau + b_t), span vector h_s = [first; last; mean;
   width]. For unseen techniques b_t is unknown: use a shared bias (and report it).
5. **Decide (D):** p_t = 1 - prod_s (1 - q_{s,t}) (noisy-OR). A full-text CLS head stays as the
   control channel, as in T4, so both modes can be compared.

Losses: Brier on q (proper), BCE on p_t, boundary loss on the proposer, CEM v2 views as now.

## Z: zero-shot technique protocol (pre-registered)

- **Z1, held-out techniques inside SemEval-2023 EN.** Split the 19 techniques into 4 folds,
  stratified by frequency and by group (argumentative vs lexical), so each fold holds out 4-5
  techniques. Train on the rest: their LABELS and SPANS are removed from training (a paragraph
  whose only technique is held out becomes technique-free for training, which is the realistic
  case). Test on dev with only the held-out definitions.
  Metrics on held-out techniques: per-technique AUROC and average precision of p_t, span-mode
  F1, evidence top-1 hit / recall@3, ECE (multi-label-corrected binning, arXiv 2609.26468).
- **Z2, cross-taxonomy transfer.** Train on all 19 SemEval techniques; test on other datasets
  using THEIR technique definitions: UNLP 2025 (10 techniques incl. new names such as Euphoria,
  Cherry Picking, FUD, Glittering Generalities; Ukrainian/Russian, so it also tests languages),
  ProBel English/Arabic (23 techniques, spans), MAFALDA (fallacies, spans).
- **Z3, definition robustness.** Re-run Z1 with 3 paraphrases of each definition; report the
  spread. (The Jev family's known failure is label-word bias, notes/jev_ecosystem.)
- Baselines: prior-only (predict the training base rate), a zero-shot NLI classifier
  (multilingual NLI model with "This text uses <definition>" as the hypothesis, paragraph level,
  no spans), a zero-shot LLM prompt (Paper 1's base Qwen3-4B with the definitions; also gives
  the speed contrast), and the SUPERVISED v3 on the same techniques (the upper bound).

## L: unseen-language alignment training (pre-registered)

Intuition: a multilingual encoder already places "they will destroy our country" and its French
translation near each other, but not close enough for span boundaries and calibrated scores to
transfer. Alignment training pulls matched pieces together explicitly.

- **Data:** translate the English training paragraphs into a few PIVOT languages (not the test
  languages) with an open MT model (NLLB or MADLAD) run locally, and carry the gold spans across
  with XML markers around each span before translation ("Just Use XML", arXiv 2603.12021);
  drop translations whose markers break.
- **Alignment losses** (on top of the task losses):
  1. Span alignment (contrastive): the vector of a gold span in English should be closest to the
     vector of the same span in the translation, among all spans in the batch (InfoNCE, tau 0.1).
  2. Decision consistency: p_t on the translation should match p_t on the English original
     (symmetric KL on the 19 Bernoulli outputs).
  3. Definitions stay in English (one set of anchors), so all languages are pulled toward the
     same technique vectors.
- **Unseen languages** = languages with no labels and no translations in training. Candidates
  (depends on what data the owner has): leave-one-language-out over the SemEval-2023 training
  languages (e.g. hold out Polish and Russian: Slavic, Russian in Cyrillic); Bulgarian from the
  Slavic corpus (arXiv 2607.10715); Arabic from ProBel; Ukrainian from UNLP 2025. The SemEval
  surprise languages (Spanish, Greek, Georgian) need test gold, which is not public; use them
  only if the official scorer is still open.
- **Calibration under language shift:** fit the temperature on the ENGLISH holdout only and
  report ECE per unseen language. SemEval-2023's best team needed separate thresholds for the
  surprise languages, so this is a real, measurable problem.
- Baselines: plain multilingual fine-tuning on English (zero-shot transfer), translate-train
  without alignment losses, translate-test (translate the input into English, run the English
  model).

## Pre-registered hypotheses and kill criteria

| Id | Claim | Kill if |
|---|---|---|
| H-Z1 | held-out techniques are detected from definitions | mean AUROC over held-out techniques < 0.65, or not above the NLI baseline (paired bootstrap CI) |
| H-Z2 | the definition judge costs nothing on seen techniques | seen-technique micro-F1 below the matched T4 by more than 0.01 (CI) |
| H-L1 | alignment training helps unseen languages | unseen-language micro-F1 or evidence recall@3 gain over translate-train-without-alignment is within the seed spread |
| H-L2 | calibration transfers | unseen-language ECE (corrected binning) with the English temperature > 0.05 |

## Order of work (each step is a kill-switch pilot first, one seed)

1. Multilingual backbone pilot (English only): does the switch cost English accuracy?
2. v3 supervised (A+C+D) vs T4 on English: H-Z2.
3. Z1 fold 1 only as a pilot; if H-Z1 survives, all 4 folds.
4. Translation + span projection pipeline, checked by hand on 50 samples per language.
5. L pilot on one held-out language; then the full grid.
6. Full study (seeds, CIs) only after the owner's approval.

## Questions for the owner

1. Which SemEval-2023 languages do you have locally with span gold (only `semeval/data/en/`
   is referenced in the code)? Is the official scorer still reachable for the surprise languages?
2. OK to run an open MT model (NLLB-200 1.3B or MADLAD-400 3B) on the 5090 for translate-train?
3. Which external sets can you download: UNLP 2025, ProBel, Slavic corpus, MAFALDA?
4. Disk: each multilingual checkpoint is about 1.1 GB; the current free space does not cover a
   full grid (see STATUS.md DISK).
