# Human audit of the CEM v2 augmentation (owner rule: audit constructed data against gold)

File to annotate: `audit_v2_sheet.csv` (165 rows, sampled with a fixed seed from the FROZEN
training pool `data/cem_v2_pool.jsonl`, SHA-256 in `data/cem_v2_pool.meta.json`). Open it in
Excel or LibreOffice (UTF-8). Do not open `audit_v2_key.json` before annotating: it says which
rows are evidence edits and which are controls.

For each row:
1. Read `original` (empty for some inserted-text rows), then `edited`.
2. Answer the `question` in column `label_correct` with `yes` or `no`, judging the EDITED text
   against the SemEval-2023 Task 3 technique definitions (annotation guidelines, Piskorski et
   al. 2023). Judge only what the question asks.
3. In `fluent`, write `yes` if the edited paragraph reads as something a writer could have
   produced (minor awkwardness is fine), `no` if the edit is obviously broken.
4. Optional `note`: why, for any `no`.

About 40 minutes for 165 rows. A second annotator on the same sheet gives agreement (kappa).

Then run: `..\torch_env\Scripts\python.exe code\cem_audit.py --v2 --score`
It writes `audit_v2_scores.json` (validity and fluency per family, with Wilson 95% intervals)
and `soft_targets.json`: the audited validity of each evidence family that passes the 0.8 bar,
used as the soft target in training (`train.py --cem v2 --soft-json results\cem_audit\soft_targets.json`).
Families below 0.8 are listed as "drop from training".

The older `audit_sheet.csv` samples CEM v1 (the pilot's augmentation); annotating it is only
needed to quantify how noisy v1 was.

## AI pre-annotation (2026-09-24) - NOT the human audit

`audit_v2_sheet_claude.csv` is a first pass by Claude, done blind (the key was not opened before
annotating), at the owner's request, for the owner to check later. Every row carries
`annotator = claude (AI pre-annotation, not human)` and a `confidence` (high/medium/low) to
prioritise the review. Scored with `code/cem_audit.py --v2 --score --tag _claude` into
`audit_v2_scores_claude.json` and `soft_targets_claude.json`; the human outputs
(`audit_v2_scores.json`, `soft_targets.json`) are untouched. Do not train on or report the
`_claude` numbers as a human audit. Once corrected, the owner's copy becomes
`audit_v2_sheet.csv`, and the AI pass can serve as the second annotator for kappa.

Rules used: label_correct judges the whole edited text against the SemEval-2023 definitions
(so KILL fails if another instance of the technique remains, and SWAP needs both halves);
fluent = no only when the edit breaks a sentence or leaves a dangling fragment. A pejorative
label that is not attached to any target was not counted as Name_Calling.
