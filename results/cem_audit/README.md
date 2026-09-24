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
