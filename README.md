# jevpersuation (working title)

**Grounded, calibrated, non-generative persuasion-technique detection with evidence-span attribution.**

A lightweight encoder (no text generation) that, for a paragraph, outputs (1) a calibrated
probability per persuasion technique, and (2) calibrated probabilities that specific
evidence spans in the paragraph support each technique. Because it predicts span boundaries
inside the input rather than generating text, every emitted evidence span is an exact
substring of the source: grounded by construction, so there is no free-text to hallucinate.
It is fast (one encoder forward pass, discourse parse cached per article) and points to
evidence with calibrated certainty.

This project is the non-generative, calibrated counterpart to Paper 1 (the faithfulness
causal-audit paper, `sftgrpo/`), which used the SAME span-level technique gold with a
generative LLM. See `IDEA.md` for the full arc.

## Start here (new session)

Read `HANDOFF.md` first. It states the owner's intent, the current stage, what is built and
verified, what is next, how to run everything, and every operating constraint (including the
GPU-unload rule and the read-only boundaries). `README.md` is the layout map; `SCOPE.md` the
design; `STATUS.md` the decision log.

## Standard paper layout

| Path | What lives here |
|---|---|
| `HANDOFF.md` | Resume point for a new session: intent, stage, what is built/verified, what is next, how to run, constraints |
| `IDEA.md` | The concept, the novelty map, and the Paper 1 to jevpersuation arc |
| `SCOPE.md` | Model, heads, training (CEA), evaluation, ablation ladder, controls, data, in/out of scope |
| `MVP_PLAN.md` | The kill-switch pilot: what to build, on what slice, what to measure, kill criteria, budget |
| `LIT_REVIEW.md` | Closest neighbors with explicit distinctions (DAVinCI, conformal multi-label, etc.) |
| `STATUS.md` | Stage, dated decisions, safe claims / do-not-claim, lessons |
| `code/` | This project's code: `augment.py` (CEM), `data.py`, `model.py` (JevPersuader v2), `train.py`, `evaluate.py`, `compare.py`, `llm_contrast.py`, `cpu_test.py`, `run_pilot.ps1`, `build_span_jsonl.py` (copied builder). See HANDOFF.md for what each is verified by |
| `logs/` | Launcher logs (not results) |
| `data/` | Project-local derived data only (processed spans, eval splits). Raw gold stays read-only |
| `results/` | One canonical table per experiment; superseded numbers struck through with a pointer |
| `paper/` | Manuscript and figures |
| `notes/` | Working notes, design memos |
| `_lit/` | Reference PDFs and notes on closest work |

## Operating constraint (set by the owner, 2026-09-23)

- All work happens inside this folder. Nothing is written outside `jevpersuation/`.
- Paper 1 (`sftgrpo/`, `finalsftgrpo/`) and the shared span gold (`semeval/data/en/`,
  `Datasets/Raw/SemEval2023_Task3/en/`) are **read-only references**.
- Reuse means **copy**: any Paper 1 span code or data needed here is copied into
  `code/` or `data/` first, then adapted. Originals are never modified.

## Read-only references (do not edit)

- Span gold (train + dev): `../semeval/data/en/train_subtask3_spans.jsonl`,
  `../semeval/data/en/train-labels-subtask-3-spans/`, `../semeval/data/en/dev-labels-subtask-3-spans/`
- Span builder: `../semeval/build_subtask3_span_jsonl.py`
- Paper 1 span infra (copy source): `../sftgrpo/finalsftgrpo/src/`
  (`config.py`, `data_io.py`, `span_faithfulness.py`, `rewards.py`, `output_parser.py`, `leak_detect.py`)
- Paper 1 held-out span eval sets: `../sftgrpo/finalsftgrpo/data/heldout_gold_spans.json`
  and the `ood_*_spans.json` files
