#!/usr/bin/env python3
"""Validate pdf-parse results against the case contract and internal evidence.

Standard library only. The case output_contract always takes precedence over the
fallback schema. The validator never changes the result and never invents data.

Usage:
    python3 validate_result.py /app/output/result.json --case /input/case.json \
        --layout /app/work/layout.json

Exit codes: 0 = no violations, 1 = violations or unreadable input, 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ID_COLLECTIONS = {
    "paragraphs": "paragraph_id", "sections": "section_id", "tables": "table_id",
    "figures": "figure_id", "formulas": "formula_id", "references": "ref_id",
    "footnotes": "footnote_id", "uncertain_items": "item_id",
}


def find_key(obj: Any, wanted: str) -> Any:
    if isinstance(obj, dict):
        if wanted in obj:
            return obj[wanted]
        for value in obj.values():
            found = find_key(value, wanted)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = find_key(value, wanted)
            if found is not None:
                return found
    return None


def is_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True


def resolve_ref(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return schema
    target: Any = root
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(target, dict) or part not in target:
            return {}
        target = target[part]
    return target if isinstance(target, dict) else {}


def validate_schema(value: Any, schema: Any, root: dict[str, Any], path: str, errors: list[dict[str, str]]) -> None:
    if not isinstance(schema, dict):
        return
    schema = resolve_ref(schema, root)
    if not schema:
        return

    expected = schema.get("type")
    if expected is not None:
        choices = expected if isinstance(expected, list) else [expected]
        if not any(is_type(value, choice) for choice in choices):
            errors.append({"path": path, "issue": f"expected type {choices}, got {type(value).__name__}"})
            return
    if "const" in schema and value != schema["const"]:
        errors.append({"path": path, "issue": f"expected constant {schema['const']!r}"})
    if "enum" in schema and value not in schema["enum"]:
        errors.append({"path": path, "issue": f"value {value!r} not in {schema['enum']}"})

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append({"path": path, "issue": f"string shorter than {schema['minLength']}"})
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append({"path": path, "issue": f"string does not match {schema['pattern']}"})
    if is_type(value, "number"):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append({"path": path, "issue": f"value below minimum {schema['minimum']}"})
        if "maximum" in schema and value > schema["maximum"]:
            errors.append({"path": path, "issue": f"value above maximum {schema['maximum']}"})

    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append({"path": path, "issue": f"missing required key: {key}"})
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for key, child in properties.items():
                if key in value:
                    validate_schema(value[key], child, root, f"{path}.{key}", errors)
        additional = schema.get("additionalProperties", True)
        if additional is False and isinstance(properties, dict):
            for key in value:
                if key not in properties:
                    errors.append({"path": f"{path}.{key}", "issue": "additional property is forbidden"})
        elif isinstance(additional, dict) and isinstance(properties, dict):
            for key in value:
                if key not in properties:
                    validate_schema(value[key], additional, root, f"{path}.{key}", errors)

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append({"path": path, "issue": f"array has fewer than {schema['minItems']} items"})
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append({"path": path, "issue": f"array has more than {schema['maxItems']} items"})
        if schema.get("uniqueItems"):
            serialized = [json.dumps(item, ensure_ascii=False, sort_keys=True) for item in value]
            if len(serialized) != len(set(serialized)):
                errors.append({"path": path, "issue": "array items are not unique"})
        if "items" in schema:
            for index, item in enumerate(value):
                validate_schema(item, schema["items"], root, f"{path}[{index}]", errors)


def normalize_contract(contract: Any) -> tuple[dict[str, Any] | None, str | None]:
    """Return a JSON-Schema-like contract, or (None, warning) for unknown shapes."""
    if isinstance(contract, dict) and isinstance(contract.get("schema"), dict):
        contract = contract["schema"]
    if isinstance(contract, dict) and ("properties" in contract or "required" in contract):
        return contract, None
    fields = contract if isinstance(contract, list) else contract.get("fields") if isinstance(contract, dict) else None
    if isinstance(fields, list):
        required, properties = [], {}
        for field in fields:
            if isinstance(field, str):
                required.append(field)
                properties[field] = {}
            elif isinstance(field, dict) and isinstance(field.get("name"), str):
                name = field["name"]
                if field.get("required", True):
                    required.append(name)
                prop: dict[str, Any] = {}
                if isinstance(field.get("type"), str):
                    prop["type"] = field["type"]
                if "enum" in field:
                    prop["enum"] = field["enum"]
                properties[name] = prop
        return {"type": "object", "required": required, "properties": properties}, None
    if contract is None:
        return None, None
    return None, "output_contract shape is not recognized; required fields could not be checked automatically"


def split_markdown_row(line: str) -> list[str]:
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|") and not text.endswith("\\|"):
        text = text[:-1]
    cells, current, escaped = [], [], False
    for char in text:
        if escaped:
            current.extend(["\\", char])
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if escaped:
        current.append("\\")
    cells.append("".join(current).strip())
    return cells


def canonical_cell(text: str) -> str:
    text = text.replace("\\|", "|").replace("<br>", " ").replace("<br/>", " ")
    return re.sub(r"\s+", " ", text).strip()


def check_table(table: dict[str, Any], path: str, errors: list[dict[str, str]]) -> None:
    cells = table.get("cells")
    if not isinstance(cells, list) or not cells:
        if table.get("markdown"):
            errors.append({"path": f"{path}.cells", "issue": "nonempty Markdown table has no cell grid"})
        return
    valid_cells = [c for c in cells if isinstance(c, dict) and all(isinstance(c.get(k), int) and not isinstance(c.get(k), bool) for k in ("row", "col", "rowspan", "colspan"))]
    if len(valid_cells) != len(cells) or not valid_cells:
        return  # schema validation reports malformed cells
    rows = max(c["row"] + c["rowspan"] - 1 for c in valid_cells)
    cols = max(c["col"] + c["colspan"] - 1 for c in valid_cells)
    grid: list[list[str | None]] = [[None for _ in range(cols)] for _ in range(rows)]
    for index, cell in enumerate(valid_cells):
        for row in range(cell["row"] - 1, cell["row"] + cell["rowspan"] - 1):
            for col in range(cell["col"] - 1, cell["col"] + cell["colspan"] - 1):
                if row >= rows or col >= cols:
                    continue
                if grid[row][col] is not None:
                    errors.append({"path": f"{path}.cells[{index}]", "issue": f"overlapping cell at row {row + 1}, col {col + 1}"})
                else:
                    grid[row][col] = str(cell.get("text", ""))
    for row_index, row in enumerate(grid):
        for col_index, text in enumerate(row):
            if text is None:
                errors.append({"path": f"{path}.cells", "issue": f"grid hole at row {row_index + 1}, col {col_index + 1}; record an explicit empty cell"})

    markdown = table.get("markdown")
    if not isinstance(markdown, str) or not markdown.strip():
        errors.append({"path": f"{path}.markdown", "issue": "structured cells exist but Markdown is empty"})
        return
    lines = [line for line in markdown.splitlines() if line.strip()]
    if len(lines) < 2:
        errors.append({"path": f"{path}.markdown", "issue": "Markdown table needs a header and separator"})
        return
    md_rows = [split_markdown_row(lines[0])] + [split_markdown_row(line) for line in lines[2:]]
    separators = split_markdown_row(lines[1])
    if not separators or not all(re.fullmatch(r":?-+:?", item.replace(" ", "")) for item in separators):
        errors.append({"path": f"{path}.markdown", "issue": "second Markdown row is not a valid separator"})
    if len(md_rows) != rows:
        errors.append({"path": f"{path}.markdown", "issue": f"logical row count {len(md_rows)} != cell grid {rows}"})
    for row_index, md_row in enumerate(md_rows):
        if len(md_row) != cols:
            errors.append({"path": f"{path}.markdown", "issue": f"row {row_index + 1} has {len(md_row)} columns, expected {cols}"})
            continue
        if row_index >= rows:
            continue
        for col_index, md_text in enumerate(md_row):
            source_text = grid[row_index][col_index]
            if source_text is not None and canonical_cell(md_text) != canonical_cell(source_text):
                errors.append({"path": f"{path}.markdown", "issue": f"cell mismatch at row {row_index + 1}, col {col_index + 1}: {md_text!r} != {source_text!r}"})


def canonical_source(text: str) -> str:
    return re.sub(r"\s+", "", text)


def layout_body(layout: dict[str, Any]) -> tuple[str, str]:
    chunks = []
    for page in layout.get("pages", []):
        if not isinstance(page, dict):
            continue
        blocks = {b.get("block_id"): b for b in page.get("blocks", []) if isinstance(b, dict)}
        for block_id in page.get("reading_order", []):
            block = blocks.get(block_id)
            if block and isinstance(block.get("text"), str):
                chunks.append(block["text"])
    joined = "\n".join(chunks)
    # Variant for documented dehyphenation across a soft line break.
    dehyphenated = re.sub(r"-\s*\n\s*", "", joined)
    return canonical_source(joined), canonical_source(dehyphenated)


def cross_checks(data: dict[str, Any], layout: dict[str, Any] | None, full_fallback: bool, errors: list[dict[str, str]], warnings: list[dict[str, str]]) -> None:
    def add(path: str, issue: str) -> None:
        errors.append({"path": path, "issue": issue})

    identifiers: dict[str, set[str]] = {}
    for collection, id_key in ID_COLLECTIONS.items():
        values = data.get(collection)
        if not isinstance(values, list):
            continue
        seen: set[str] = set()
        for index, item in enumerate(values):
            if not isinstance(item, dict):
                continue
            identifier = item.get(id_key)
            if isinstance(identifier, str):
                if identifier in seen:
                    add(f"$.{collection}[{index}].{id_key}", f"duplicate ID {identifier}")
                seen.add(identifier)
        identifiers[collection] = seen

    paragraph_ids = identifiers.get("paragraphs", set())
    section_ids = identifiers.get("sections", set())
    memberships: dict[str, int] = {pid: 0 for pid in paragraph_ids}
    for index, section in enumerate(data.get("sections", [])):
        if not isinstance(section, dict):
            continue
        if isinstance(section.get("page_start"), int) and isinstance(section.get("page_end"), int) and section["page_start"] > section["page_end"]:
            add(f"$.sections[{index}]", "page_start is after page_end")
        for pid in section.get("paragraph_ids", []):
            if pid not in paragraph_ids:
                add(f"$.sections[{index}].paragraph_ids", f"unknown paragraph ID {pid!r}")
            else:
                memberships[pid] += 1
    for index, paragraph in enumerate(data.get("paragraphs", [])):
        if not isinstance(paragraph, dict):
            continue
        pid = paragraph.get("paragraph_id")
        sid = paragraph.get("section_id")
        if sid is not None and sid not in section_ids:
            add(f"$.paragraphs[{index}].section_id", f"unknown section ID {sid!r}")
        if isinstance(pid, str) and sid is not None and memberships.get(pid, 0) == 0:
            add(f"$.paragraphs[{index}]", "section_id is set but no section lists this paragraph")
        if isinstance(pid, str) and memberships.get(pid, 0) > 1:
            add(f"$.paragraphs[{index}]", "paragraph is listed in multiple sections")

    coverage = data.get("coverage")
    total = None
    if isinstance(coverage, dict):
        total = coverage.get("pages_total")
        attempted = set(coverage.get("pages_attempted", []))
        completed = set(coverage.get("pages_completed", []))
        failed = set(coverage.get("pages_failed", []))
        if isinstance(total, int):
            expected = set(range(1, total + 1))
            for name, pages in (("attempted", attempted), ("completed", completed), ("failed", failed)):
                if not pages <= expected:
                    add(f"$.coverage.pages_{name}", "page number outside 1..pages_total")
            if completed & failed:
                add("$.coverage", "pages_completed and pages_failed overlap")
            if completed | failed != attempted:
                add("$.coverage", "completed + failed must partition attempted pages")
            if data.get("task_status") == "success" and (completed != expected or failed or attempted != expected):
                add("$.task_status", "success requires every page attempted and completed, with no failed page")
        document = data.get("document")
        if isinstance(document, dict) and isinstance(document.get("page_count"), int) and total != document["page_count"]:
            add("$.coverage.pages_total", "does not equal document.page_count")

    for collection in ("paragraphs", "tables", "figures", "formulas", "references", "footnotes"):
        items = data.get(collection)
        if not isinstance(items, list):
            continue
        for index, item in enumerate(items):
            if not isinstance(item, dict) or not isinstance(item.get("locations"), list):
                continue
            for loc_index, location in enumerate(item["locations"]):
                if not isinstance(location, dict):
                    continue
                page = location.get("pdf_page")
                if isinstance(total, int) and isinstance(page, int) and not 1 <= page <= total:
                    add(f"$.{collection}[{index}].locations[{loc_index}].pdf_page", "page outside coverage.pages_total")
                bbox = location.get("bbox")
                if isinstance(bbox, list) and len(bbox) == 4 and all(is_type(x, "number") for x in bbox):
                    if bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
                        add(f"$.{collection}[{index}].locations[{loc_index}].bbox", "bbox must satisfy xMin < xMax and yMin < yMax")

    tables = data.get("tables")
    if isinstance(tables, list):
        for index, table in enumerate(tables):
            if isinstance(table, dict):
                check_table(table, f"$.tables[{index}]", errors)

    quality = data.get("quality_check")
    if isinstance(quality, dict):
        issues = quality.get("issues")
        if isinstance(issues, list):
            if quality.get("issue_count") != len(issues):
                add("$.quality_check.issue_count", "does not equal len(issues)")
            if quality.get("pass") is True and issues:
                add("$.quality_check.pass", "cannot be true when issues are present")
            if quality.get("pass") is False and not issues:
                add("$.quality_check.pass", "false requires at least one recorded issue")
        if data.get("task_status") == "success" and quality.get("pass") is not True:
            add("$.task_status", "success requires quality_check.pass=true")

    uncertainties = data.get("uncertain_items")
    if isinstance(uncertainties, list):
        for index, item in enumerate(uncertainties):
            if not isinstance(item, dict):
                continue
            if data.get("task_status") == "success" and item.get("impact_level") == "high":
                add(f"$.uncertain_items[{index}].impact_level", "success cannot retain a high-impact unresolved item")
            if item.get("item_type") == "ocr_corrected":
                if not item.get("raw_text") or not item.get("corrected_text"):
                    add(f"$.uncertain_items[{index}]", "ocr_corrected requires raw_text and corrected_text")
                elif item["raw_text"] == item["corrected_text"]:
                    add(f"$.uncertain_items[{index}]", "ocr_corrected raw and corrected text are identical")

    if full_fallback and data.get("task_status") == "success" and not data.get("paragraphs"):
        add("$.paragraphs", "a successful full-document parse cannot have an empty paragraph array")

    if layout is not None:
        source_variants = layout_body(layout)
        for index, paragraph in enumerate(data.get("paragraphs", [])):
            if not isinstance(paragraph, dict) or paragraph.get("source_type") != "text_layer":
                continue
            text = paragraph.get("text")
            if isinstance(text, str) and text.strip():
                candidate = canonical_source(text)
                if not any(candidate and candidate in source for source in source_variants):
                    add(f"$.paragraphs[{index}].text", "text is not traceable to the supplied layout evidence (possible template, fabrication, or unsupported merge)")
        sources = data.get("sources")
        if isinstance(sources, list) and isinstance(layout.get("source_sha256"), str):
            hashes = {s.get("sha256") for s in sources if isinstance(s, dict) and s.get("role") == "source_pdf"}
            if hashes and layout["source_sha256"] not in hashes:
                add("$.sources", "source PDF hash does not match the supplied layout evidence")
        empty_pages = set((layout.get("coverage_hint") or {}).get("pages_without_body_text", []))
        if isinstance(coverage, dict) and empty_pages:
            completed = set(coverage.get("pages_completed", []))
            if empty_pages & completed and not any(isinstance(u, dict) and u.get("item_type") in {"unreadable", "missing_section", "partial_coverage"} for u in uncertainties or []):
                add("$.coverage.pages_completed", "layout reports textless pages but no OCR/unreadable/partial-coverage item explains their completion")


def validate(data: Any, case: dict[str, Any] | None, layout: dict[str, Any] | None, fallback_schema: dict[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    if not isinstance(data, dict):
        return [{"path": "$", "issue": "root must be a JSON object"}], warnings

    contract = find_key(case, "output_contract") if case else None
    contract_schema, contract_warning = normalize_contract(contract)
    if contract_warning:
        warnings.append({"path": "$.output_contract", "issue": contract_warning})

    if contract_schema is not None:
        validate_schema(data, contract_schema, contract_schema, "$", errors)
        # Validate any recognized rich fields that the contract permits, without
        # imposing the fallback schema's required keys.
        for key, subschema in fallback_schema.get("properties", {}).items():
            if key in data:
                validate_schema(data[key], subschema, fallback_schema, f"$.{key}", errors)
        full_fallback = False
    elif contract is not None:
        # An unrecognized but real contract still takes precedence: never force
        # our fallback required fields onto it. Check only recognized rich fields.
        for key, subschema in fallback_schema.get("properties", {}).items():
            if key in data:
                validate_schema(data[key], subschema, fallback_schema, f"$.{key}", errors)
        full_fallback = False
    else:
        validate_schema(data, fallback_schema, fallback_schema, "$", errors)
        full_fallback = True

    if case:
        expected_id = find_key(case, "case_id")
        if expected_id is not None and data.get("case_id") != expected_id:
            errors.append({"path": "$.case_id", "issue": f"must exactly equal case.json case_id {expected_id!r}"})
    cross_checks(data, layout, full_fallback, errors, warnings)
    return errors, warnings


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("--case", type=Path)
    parser.add_argument("--layout", type=Path)
    parser.add_argument("--schema", type=Path, default=Path(__file__).resolve().parent.parent / "references" / "result.schema.json")
    args = parser.parse_args()
    try:
        data = load_json(args.result)
        case = load_json(args.case) if args.case else None
        layout = load_json(args.layout) if args.layout else None
        fallback_schema = load_json(args.schema)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"path": "$", "issue": f"cannot read input: {exc}"}, ensure_ascii=False))
        return 1
    errors, warnings = validate(data, case, layout, fallback_schema)
    for item in errors:
        print(json.dumps({"severity": "error", **item}, ensure_ascii=False))
    for item in warnings:
        print(json.dumps({"severity": "warning", **item}, ensure_ascii=False))
    if errors:
        print(f"validation failed: {len(errors)} error(s), {len(warnings)} warning(s)", file=sys.stderr)
        return 1
    print(f"validation passed: 0 errors, {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
