#!/usr/bin/env python3
"""Extract auditable PDF text blocks and propose a column-aware reading order.

Runtime dependencies: Python 3 standard library and Poppler's pdftotext.
Optional rendering uses pdftoppm. This script does not OCR and does not interpret
scientific meaning. Its header/footer and reading-order labels are proposals that
must be checked against rendered pages before they become final results.

Usage:
    python3 extract_pdf.py INPUT.pdf /app/work/layout.json
    python3 extract_pdf.py INPUT.pdf /app/work/layout.json --render-dir /app/work/pages
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

VERSION = "pdf-parse-layout@2.0.0"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def children(element: ET.Element, name: str) -> Iterable[ET.Element]:
    return (child for child in element.iter() if local_name(child.tag) == name)


def number(element: ET.Element, key: str) -> float:
    return float(element.attrib[key])


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def run(command: list[str], timeout: int) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)


def decode(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_blocks(page: ET.Element, page_number: int) -> tuple[float, float, list[dict[str, Any]]]:
    width = number(page, "width")
    height = number(page, "height")
    blocks: list[dict[str, Any]] = []
    for xml_block in children(page, "block"):
        try:
            bbox = [number(xml_block, key) for key in ("xMin", "yMin", "xMax", "yMax")]
        except (KeyError, ValueError):
            continue
        lines = []
        line_bboxes = []
        for xml_line in children(xml_block, "line"):
            words = []
            for xml_word in children(xml_line, "word"):
                # itertext preserves entities and any nested text without inventing content.
                words.append("".join(xml_word.itertext()))
            if words:
                lines.append(" ".join(words))
                try:
                    line_bboxes.append([round(number(xml_line, key), 3) for key in ("xMin", "yMin", "xMax", "yMax")])
                except (KeyError, ValueError):
                    line_bboxes.append(None)
        text = "\n".join(lines).strip()
        if not text:
            continue
        block_id = f"p{page_number}-b{len(blocks) + 1:03d}"
        blocks.append({
            "block_id": block_id,
            "text": text,
            "lines": lines,
            "line_bboxes": line_bboxes,
            "bbox": [round(x, 3) for x in bbox],
            "kind": "body",
            "column": 0,
            "order": None,
        })
    return width, height, blocks


def mark_repeated_margins(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mark, never silently delete, repeated text in the top/bottom 12% margin."""
    occurrences: dict[tuple[str, str], list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for page in pages:
        height = page["height"]
        for block in page["blocks"]:
            x0, y0, x1, y1 = block["bbox"]
            center_y = (y0 + y1) / 2
            zone = "header" if center_y <= height * 0.12 else "footer" if center_y >= height * 0.88 else None
            if zone:
                occurrences[(zone, normalize(block["text"]))].append((page["pdf_page"], block))

    repeated = []
    for (zone, text), items in sorted(occurrences.items()):
        page_numbers = sorted({page for page, _ in items})
        # Repetition alone is insufficient outside the margin; inside the margin it
        # produces a candidate requiring visual confirmation by the Agent.
        if text and len(page_numbers) >= 2:
            for _, block in items:
                block["kind"] = f"{zone}_candidate"
            repeated.append({"type": zone, "text": text, "pages": page_numbers, "status": "candidate"})
    return repeated


def mark_margin_notes(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mark tall, narrow blocks at the extreme side margins as candidates."""
    candidates = []
    for page in pages:
        width = page["width"]
        for block in page["blocks"]:
            if block["kind"] != "body":
                continue
            x0, y0, x1, y1 = block["bbox"]
            block_width, block_height = x1 - x0, y1 - y0
            extreme_side = x1 <= width * 0.12 or x0 >= width * 0.88
            if extreme_side and block_height >= max(2.5 * block_width, 40):
                block["kind"] = "margin_note_candidate"
                candidates.append({"type": "margin_note", "text": block["text"],
                                   "pages": [page["pdf_page"]], "status": "candidate"})
    return candidates


def is_full_width(block: dict[str, Any], width: float) -> bool:
    x0, _, x1, _ = block["bbox"]
    middle = width / 2
    return (x1 - x0 >= width * 0.72) or (x0 <= middle - width * 0.10 and x1 >= middle + width * 0.10)


def column_segment(blocks: list[dict[str, Any]], width: float) -> list[dict[str, Any]]:
    """Order a vertical segment containing no detected full-width block."""
    if len(blocks) <= 1:
        return blocks
    middle = width / 2
    left, right, crossing = [], [], []
    for block in blocks:
        x0, _, x1, _ = block["bbox"]
        if x1 <= middle + width * 0.03:
            left.append(block)
        elif x0 >= middle - width * 0.03:
            right.append(block)
        else:
            crossing.append(block)

    # Require evidence on both sides; otherwise varying paragraph widths in a
    # single-column page must not be mistaken for two columns.
    if left and right:
        for block in left:
            block["column"] = 1
        for block in right:
            block["column"] = 2
        for block in crossing:
            block["column"] = 1 if (block["bbox"][0] + block["bbox"][2]) / 2 < middle else 2
        left.extend(block for block in crossing if block["column"] == 1)
        right.extend(block for block in crossing if block["column"] == 2)
        by_y = lambda b: (b["bbox"][1], b["bbox"][0], b["block_id"])
        return sorted(left, key=by_y) + sorted(right, key=by_y)

    by_y = lambda b: (b["bbox"][1], b["bbox"][0], b["block_id"])
    return sorted(blocks, key=by_y)


def first_line_bbox(block: dict[str, Any]) -> list[float]:
    lines = block.get("line_bboxes") or []
    if lines and isinstance(lines[0], list):
        return lines[0]
    return block["bbox"]


def reading_order(blocks: list[dict[str, Any]], width: float) -> tuple[list[dict[str, Any]], str]:
    body = [block for block in blocks if block["kind"] == "body"]
    if not body:
        return [], "no_text"
    full = sorted((block for block in body if is_full_width(block, width)), key=lambda b: (b["bbox"][1], b["bbox"][0]))
    ordinary = [block for block in body if block not in full]
    for block in full:
        block["column"] = 0

    if not full:
        ordered = column_segment(ordinary, width)
        layout = "two_column" if any(b["column"] == 1 for b in ordered) and any(b["column"] == 2 for b in ordered) else "single_column"
        return ordered, layout

    ordered: list[dict[str, Any]] = []
    remaining = ordinary[:]
    for wide in full:
        wide_y = wide["bbox"][1]
        wide_first = first_line_bbox(wide)
        first_line_height = max(1.0, wide_first[3] - wide_first[1])
        # Poppler sometimes splits text on the same first line (for example,
        # author names) into a wide block plus a small block. Keep such companions
        # in one band and sort by the FIRST line's x coordinate, not the minimum
        # x of a multi-line block (which may come from a later affiliation line).
        companions = [b for b in remaining
                      if b["bbox"][1] <= wide_y + 0.6 * first_line_height
                      and b["bbox"][3] <= wide_y + 2.0 * first_line_height
                      and b["bbox"][3] >= wide_y]
        companion_ids = {b["block_id"] for b in companions}
        before = [b for b in remaining if b["block_id"] not in companion_ids
                  and (b["bbox"][1] + b["bbox"][3]) / 2 < wide_y]
        if before:
            ordered.extend(column_segment(before, width))
            before_ids = {b["block_id"] for b in before}
            remaining = [b for b in remaining if b["block_id"] not in before_ids]
        band = companions + [wide]
        band.sort(key=lambda b: (first_line_bbox(b)[1], first_line_bbox(b)[0], b["block_id"]))
        ordered.extend(band)
        remaining = [b for b in remaining if b["block_id"] not in companion_ids]
    if remaining:
        ordered.extend(column_segment(remaining, width))
    return ordered, "mixed_width"


def extract(pdf_path: Path, timeout: int, render_dir: Path | None) -> dict[str, Any]:
    if not pdf_path.is_file():
        raise ValueError(f"PDF not found: {pdf_path}")
    executable = shutil.which("pdftotext")
    if not executable:
        raise RuntimeError("pdftotext is unavailable; use the platform pdf-text-tool or install Poppler")

    completed = run([executable, "-bbox-layout", "-enc", "UTF-8", str(pdf_path), "-"], timeout)
    if completed.returncode != 0:
        message = decode(completed.stderr).strip()
        if "Incorrect password" in message or "encrypted" in message.lower():
            raise RuntimeError(f"encrypted or password-protected PDF: {message}")
        raise RuntimeError(f"pdftotext failed ({completed.returncode}): {message}")
    if not completed.stdout.strip():
        raise RuntimeError("pdftotext returned no XHTML; inspect the PDF and use OCR if it has no text layer")

    try:
        root = ET.fromstring(completed.stdout)
    except ET.ParseError as exc:
        raise RuntimeError(f"cannot parse pdftotext XHTML: {exc}") from exc

    pages = []
    for index, xml_page in enumerate(children(root, "page"), start=1):
        width, height, blocks = parse_blocks(xml_page, index)
        pages.append({"pdf_page": index, "width": width, "height": height, "blocks": blocks,
                      "layout": "unknown", "reading_order": []})
    if not pages:
        raise RuntimeError("the PDF contains no pages in pdftotext output")

    repeated = mark_repeated_margins(pages)
    repeated.extend(mark_margin_notes(pages))
    for page in pages:
        ordered, layout = reading_order(page["blocks"], page["width"])
        page["layout"] = layout
        for order, block in enumerate(ordered, start=1):
            block["order"] = order
            page["reading_order"].append(block["block_id"])
        # Candidates remain in blocks with their original coordinates but are not
        # silently inserted into body reading order.
        page["blocks"].sort(key=lambda b: b["block_id"])

    rendered = []
    if render_dir is not None:
        renderer = shutil.which("pdftoppm")
        if not renderer:
            raise RuntimeError("pdftoppm is unavailable; use the platform pdf-render-tool instead")
        render_dir.mkdir(parents=True, exist_ok=True)
        prefix = render_dir / "page"
        rendered_process = run([renderer, "-png", "-r", "150", str(pdf_path), str(prefix)], timeout)
        if rendered_process.returncode != 0:
            raise RuntimeError(f"pdftoppm failed: {decode(rendered_process.stderr).strip()}")
        rendered = [str(path) for path in sorted(render_dir.glob("page-*.png"))]

    version_process = run([executable, "-v"], 10)
    version_text = decode(version_process.stderr or version_process.stdout).splitlines()
    empty_pages = [page["pdf_page"] for page in pages if not page["reading_order"]]
    warnings = []
    if empty_pages:
        warnings.append({"type": "no_text_layer_or_margin_only", "pages": empty_pages,
                         "action": "render and OCR these pages; do not mark them successfully extracted"})
    return {
        "layout_version": VERSION,
        "source_pdf": str(pdf_path.resolve()),
        "source_sha256": sha256(pdf_path),
        "extractor": {
            "name": "pdftotext",
            "version": version_text[0] if version_text else "unknown",
            "command": "pdftotext -bbox-layout -enc UTF-8 INPUT.pdf -",
        },
        "page_count": len(pages),
        "coverage_hint": {
            "pages_with_body_text": [p["pdf_page"] for p in pages if p["reading_order"]],
            "pages_without_body_text": empty_pages,
        },
        "headers_footers_candidates": repeated,
        "rendered_pages": rendered,
        "pages": pages,
        "warnings": warnings,
        "limitations": [
            "Text and coordinates come from the PDF text layer, not from independent OCR verification.",
            "Reading order and repeated-margin labels are deterministic proposals requiring visual review.",
            "Tables and formulas are not semantically reconstructed by this script.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--render-dir", type=Path)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    try:
        result = extract(args.pdf, args.timeout, args.render_dir)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(json.dumps({
        "status": "ok",
        "page_count": result["page_count"],
        "body_block_count": sum(len(p["reading_order"]) for p in result["pages"]),
        "empty_pages": result["coverage_hint"]["pages_without_body_text"],
        "output": str(args.output),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
