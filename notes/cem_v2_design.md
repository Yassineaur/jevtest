# CEM v2: counterfactual evidence augmentation without artifacts (design, 2026-09-23)

Owner's ask: "find the best solution for augmented data so that we don't have any problem or
concern with this part." v1 (`code/augment.py`) stays frozen so the pilot stays reproducible;
v2 lives in `code/augment_v2.py`.

## Problems found in v1 (from the first audit sample, `results/cem_audit/`)

1. Edits are often ungrammatical: word swaps ("shot two made, officers"), cues pasted mid-phrase
   ("echoed became "frantic the FDD"), holes left by moved spans ("the actions of  .").
2. A model can learn "edited text -> technique" (shortcut): v1 has evidence edits but no
   matched non-evidence edits in training.
3. Label rules are unaudited: injected or swapped spans may lose their technique out of
   context (Doubt, Whataboutism, Red Herring depend on context); deletion assumes the
   annotation is exhaustive.
4. The same edit families train and test faithfulness (circular).
5. Views are resampled every epoch, so no one can audit what was actually trained on.

## v2 rules

**Edit points.** Insertions and relocations happen only at sentence boundaries or DMRST EDU
boundaries of the original paragraph (never mid-phrase). Deleted evidence takes a following
space or punctuation-safe join; no double spaces or orphan punctuation are left.

**Families (training).** For each (paragraph, technique t with exactly one located gold span s):
- KILL: delete s -> t off.                          KILL-CTRL: delete a same-length
  non-evidence chunk at a boundary -> labels unchanged.
- INJECT (into a t-negative paragraph): insert a real train-fit gold span of t at a boundary
  -> t on.                                           INJECT-CTRL: insert a same-length
  non-evidence chunk from another train-fit paragraph at the same boundary -> unchanged.
- SWAP: replace s with a gold span of t' -> t off, t' on. SWAP-CTRL: replace a same-length
  non-evidence chunk with a non-evidence chunk -> unchanged.
Each evidence edit has its control of the same kind and size, so the presence of an edit is
uninformative about the label (artifact-balanced by construction).

**Fluency filter.** Every candidate view is scored with GPT-2 (124M) mean token NLL; a view is
kept only if NLL(edited) - NLL(original) <= FLUENCY_MAX (set on the train pool so that the
evidence edits and their controls pass at similar rates; both rates reported). Controls pass
the SAME filter, so filtering cannot create a gap between them.

**Label validity.** The audit sheet samples the frozen pool (30 per family, stratified). Per
family: human-judged validity with a Wilson 95% interval. Families with validity < 0.8 are
dropped; kept families use a SOFT target equal to the audited validity for the edited technique
(BCE's optimum is then the true expected label, so the noise cannot miscalibrate p_t). Until the
audit is done, targets stay hard and every result using v2 is marked "unaudited".

**Frozen pool.** Generated once from the train-fit split with a fixed seed: 2 evidence views and
their controls per eligible (paragraph, technique), plus INJECT pairs for every technique. Saved
to `data/cem_v2_pool.jsonl` with its SHA-256 in `data/cem_v2_pool.meta.json`. Each epoch samples
from the pool; V0 originals always make up at least a third of an epoch.

**Evaluation families held out from training.** Faithfulness is judged on:
- RELOCATE (move s to another boundary; label must stay) vs RELOCATE-CTRL (move a non-evidence
  chunk);
- SUFFICIENCY (ERASER): p_t on the evidence span alone vs a same-length random chunk alone;
- COMPREHENSIVENESS on the model's own top span vs a same-length control (already built);
- KILL and INJECT with their controls are reported too, but flagged as trained families.
Dev paragraphs are never used to fit the fluency threshold or anything else.
