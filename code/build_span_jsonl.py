#!/usr/bin/env python3
# COPIED 2026-09-23 from ../semeval/build_subtask3_span_jsonl.py (read-only original, unchanged logic).
"""Merge SemEval-2023 task-3 paragraph labels with character-span annotations.

Reads:
  - {split}-articles-subtask-3/article{ID}.txt  — full article text (span offsets apply here)
  - {split}-labels-subtask-3-spans/article{ID}-labels-subtask-3.txt — tab: id, technique, start, end
  - {split}-labels-subtask-3/article{ID}-labels-subtask-3.txt — tab: id, paragraph_line_id, techniques

Each JSONL row is one **paragraph** listed in SemEval ``train-labels-subtask-3`` for that article
(one row per line in ``article{ID}-labels-subtask-3.txt``).

By default, rows with **no** ``paragraph_techniques`` and **no** ``spans`` are **dropped** (pass
``--keep-empty-paragraphs`` to retain them). Optional ``--chunks-dir`` writes sharded ``part_XXXXX.jsonl``
files with ``--chunk-size`` lines each (after filtering).

Offsets from the ``*-spans/`` files are used only when reading; output span entries use ``text``, not
coordinates.

- ``id``: ``"{article_id}:{paragraph_id}"``.
- ``article_id``, ``paragraph_id``: as in the task gold.
- ``paragraph_text``: text of that physical line. If a span crosses a soft line wrap, it is grouped
  under the line where that span **starts**; that span's ``text`` may extend beyond ``paragraph_text``.
- ``paragraph_techniques``: from the paragraph-labels file for that line.
- ``spans``: list of ``{"text": <substring>, "technique": <label>}`` from the spans folder, ordered by
  position; empty when no spans are annotated for that paragraph.

Output order follows the paragraph-labels file. If ``{split}-labels-subtask-3-spans`` is missing,
every ``spans`` list is empty.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, List, Tuple


def paragraph_index_from_article(article_path: Path) -> Dict[str, dict]:
    """Map paragraph id (1-based physical line index) to text and char span in the file.

    Matches ``codes/span_data.read_template_rows`` / official line indexing.
    """

    text = article_path.read_text(encoding="utf-8")
    rows: Dict[str, dict] = {}
    cursor = 0
    for idx, raw_line in enumerate(text.splitlines(keepends=True), start=1):
        line_body = raw_line.rstrip("\r\n")
        if line_body.strip():
            rows[str(idx)] = {
                "text": line_body,
                "char_start": cursor,
                "char_end": cursor + len(line_body),
            }
        cursor += len(raw_line)
    return rows


def read_paragraph_label_rows_in_order(label_path: Path) -> List[Tuple[str, List[str]]]:
    """Each gold row: (paragraph_line_id, [technique, ...]). Order is file order."""

    rows: List[Tuple[str, List[str]]] = []
    for line in label_path.read_text(encoding="utf-8").splitlines():
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 2:
            continue
        pid = parts[1].strip()
        labels = (
            [t.strip() for t in parts[2].split(",") if t.strip()]
            if len(parts) > 2 and parts[2].strip()
            else []
        )
        rows.append((pid, labels))
    return rows


def read_paragraph_techniques(label_path: Path) -> Dict[str, List[str]]:
    """Per-paragraph techniques: paragraph_line_id -> [technique, ...]."""
    return {pid: labs for pid, labs in read_paragraph_label_rows_in_order(label_path)}


def read_span_lines(spans_path: Path) -> List[Tuple[str, int, int]]:
    """Return list of (technique, start, end) for one article spans file."""
    spans: List[Tuple[str, int, int]] = []
    for line in spans_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        technique = parts[1].strip()
        start, end = int(parts[2]), int(parts[3])
        spans.append((technique, start, end))
    return spans


def find_paragraph_for_span(
    para_rows: Dict[str, dict], start: int, end: int
) -> Tuple[str, dict, bool] | None:
    """Return (paragraph_id, row, is_fully_inside_line).

    Paragraph ids match **physical non-empty lines** in the article ``.txt`` (same as
    task-3 labels). Spans sometimes cross a soft line-break between two numbered lines;
    we attach those to the line where ``start`` falls, and set ``is_fully_inside_line``
    false when the span extends past that line's ``char_end``.
    """

    for pid in sorted(para_rows.keys(), key=int):
        pr = para_rows[pid]
        ps, pe = pr["char_start"], pr["char_end"]
        if ps <= start < pe:
            full_inside = end <= pe
            return pid, pr, full_inside
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parent / "data" / "en"
    parser.add_argument(
        "--data-lang-dir",
        type=Path,
        default=default_root,
        help=f"Language data root (default: {default_root})",
    )
    parser.add_argument(
        "--split",
        choices=("train", "dev"),
        default="train",
        help="Which split folder prefix to use (train-* or dev-*)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Optional single combined .jsonl path",
    )
    parser.add_argument(
        "--chunks-dir",
        type=Path,
        default=None,
        help=(
            "Directory for sharded part_XXXXX.jsonl files (--chunk-size lines each). "
            "Relative paths resolve under --data-lang-dir."
        ),
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=5,
        help="Paragraph records per shard file (default: 5)",
    )
    parser.add_argument(
        "--keep-empty-paragraphs",
        action="store_true",
        help="Keep paragraphs with no paragraph_techniques and no spans (default: drop them)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if a span is not contained in any paragraph or technique mismatches labels",
    )
    args = parser.parse_args()
    root: Path = args.data_lang_dir

    if not args.output and not args.chunks_dir:
        print("Provide --output and/or --chunks-dir", file=sys.stderr)
        sys.exit(1)

    chunks_resolved: Path | None = None
    if args.chunks_dir is not None:
        chunks_resolved = (
            args.chunks_dir if args.chunks_dir.is_absolute() else root / args.chunks_dir
        )

    articles_dir = root / f"{args.split}-articles-subtask-3"
    labels_dir = root / f"{args.split}-labels-subtask-3"
    spans_dir = root / f"{args.split}-labels-subtask-3-spans"

    for d in (articles_dir, labels_dir):
        if not d.is_dir():
            print(f"Missing directory: {d}", file=sys.stderr)
            sys.exit(1)
    if not spans_dir.is_dir():
        print(f"Note: {spans_dir} not found; spans will all be empty.", file=sys.stderr)

    paragraph_label_files = sorted(labels_dir.glob("article*-labels-subtask-3.txt"))
    if not paragraph_label_files:
        print(f"No paragraph label files in {labels_dir}", file=sys.stderr)
        sys.exit(1)

    records: List[dict] = []
    errs = 0
    cross_line = 0

    for label_path in paragraph_label_files:
        m = re.match(r"article(\d+)-labels-subtask-3\.txt$", label_path.name)
        if not m:
            continue
        article_id = m.group(1)
        article_path = articles_dir / f"article{article_id}.txt"
        spans_path = spans_dir / f"article{article_id}-labels-subtask-3.txt"
        if not article_path.is_file():
            print(f"Missing article {article_path}", file=sys.stderr)
            errs += 1
            continue

        full_text = article_path.read_text(encoding="utf-8")
        para_rows = paragraph_index_from_article(article_path)
        label_rows = read_paragraph_label_rows_in_order(label_path)
        para_tech = read_paragraph_techniques(label_path)

        span_items_by_para: DefaultDict[str, List[Tuple[int, int, str, str]]] = defaultdict(
            list
        )

        if spans_path.is_file():
            for technique, start, end in read_span_lines(spans_path):
                if start < 0 or end > len(full_text) or start >= end:
                    print(
                        f"Bad span bounds {start},{end} for article {article_id}",
                        file=sys.stderr,
                    )
                    errs += 1
                    continue

                span_text = full_text[start:end]
                found = find_paragraph_for_span(para_rows, start, end)
                if found is None:
                    print(
                        f"Span start {start} not inside any non-empty line "
                        f"(article {article_id}, technique {technique})",
                        file=sys.stderr,
                    )
                    errs += 1
                    if args.strict:
                        sys.exit(1)
                    continue

                para_id, _pr, full_inside = found
                if not full_inside:
                    cross_line += 1
                para_labels = para_tech.get(para_id, [])
                if para_labels and technique not in para_labels:
                    print(
                        f"Warning: {technique} at [{start},{end}) not in paragraph "
                        f"{para_id} labels {para_labels} (article {article_id})",
                        file=sys.stderr,
                    )
                    if args.strict:
                        sys.exit(1)

                span_items_by_para[para_id].append((start, end, span_text, technique))

        for para_id, para_labels in label_rows:
            pr = para_rows.get(para_id)
            if not pr:
                print(
                    f"No non-empty article line {para_id} for article {article_id}",
                    file=sys.stderr,
                )
                errs += 1
                if args.strict:
                    sys.exit(1)
                continue

            raw_items = span_items_by_para.get(para_id, [])
            items = sorted(raw_items, key=lambda x: (x[0], x[1]))
            spans = [{"text": txt, "technique": tech} for _, _, txt, tech in items]

            rec = {
                "id": f"{article_id}:{para_id}",
                "article_id": article_id,
                "paragraph_id": para_id,
                "paragraph_text": pr["text"],
                "paragraph_techniques": para_labels,
                "spans": spans,
            }
            records.append(rec)

    n_full = len(records)
    if not args.keep_empty_paragraphs:
        records = [r for r in records if r["paragraph_techniques"] or r["spans"]]
    n_kept = len(records)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as out_f:
            for rec in records:
                out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"Wrote {n_kept} JSONL lines to {args.output} (from {n_full} before filter)")

    if chunks_resolved is not None:
        chunk_dir = chunks_resolved
        chunk_dir.mkdir(parents=True, exist_ok=True)
        for old in chunk_dir.glob("part_*.jsonl"):
            old.unlink()
        size = max(1, args.chunk_size)
        n_chunks = (len(records) + size - 1) // size if records else 0
        for i in range(0, len(records), size):
            part_num = i // size + 1
            path = chunk_dir / f"part_{part_num:05d}.jsonl"
            with path.open("w", encoding="utf-8") as cf:
                for rec in records[i : i + size]:
                    cf.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(
            f"Wrote {n_chunks} shard files ({size} lines each, last may be shorter) "
            f"to {chunk_dir} ({n_kept} paragraphs after filter, from {n_full} before)"
        )

    if args.output is None and chunks_resolved is not None and not records:
        print("Warning: no records after filter; chunk directory may be empty.", file=sys.stderr)

    if cross_line:
        print(
            f"Note: {cross_line} spans start on one physical line but extend past "
            f"its line break (paragraph_id = line where the span starts).",
            file=sys.stderr,
        )
    if errs:
        print(f"Completed with {errs} issues logged to stderr", file=sys.stderr)


if __name__ == "__main__":
    main()
