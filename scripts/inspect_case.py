#!/usr/bin/env python3
"""Inspect a Harbor case.json without inventing any case content.

Usage:
    python3 inspect_case.py /input/case.json --output /app/work/case_manifest.json

The manifest records the exact case_id, existing task.md candidates, PDF files,
and the unmodified output_contract. Only Python's standard library is used.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def find_key(obj: Any, wanted: str) -> Any:
    """Find the first exact key in a nested JSON object, deterministically."""
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


def existing_pdf_strings(obj: Any, base: Path) -> list[str]:
    found: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, str) and value.lower().endswith(".pdf"):
            candidate = Path(value)
            if not candidate.is_absolute():
                candidate = base / candidate
            try:
                resolved = candidate.resolve()
            except OSError:
                return
            if resolved.is_file() and resolved.suffix.lower() == ".pdf":
                found.add(str(resolved))

    walk(obj)
    return sorted(found)


def contract_summary(contract: Any) -> dict[str, Any]:
    """Summarize common JSON-Schema-like output contracts without changing them."""
    summary: dict[str, Any] = {
        "present": contract is not None,
        "shape": type(contract).__name__ if contract is not None else "none",
        "required_fields": [],
        "allow_additional": None,
    }
    schema = contract
    if isinstance(contract, dict) and isinstance(contract.get("schema"), dict):
        schema = contract["schema"]
    if isinstance(schema, dict):
        required = schema.get("required")
        if isinstance(required, list):
            summary["required_fields"] = [x for x in required if isinstance(x, str)]
        elif isinstance(schema.get("fields"), list):
            names = []
            for field in schema["fields"]:
                if isinstance(field, str):
                    names.append(field)
                elif isinstance(field, dict) and isinstance(field.get("name"), str):
                    if field.get("required", True):
                        names.append(field["name"])
            summary["required_fields"] = names
        if "additionalProperties" in schema:
            summary["allow_additional"] = bool(schema["additionalProperties"])
    elif isinstance(contract, list):
        names = []
        for field in contract:
            if isinstance(field, str):
                names.append(field)
            elif isinstance(field, dict) and isinstance(field.get("name"), str):
                if field.get("required", True):
                    names.append(field["name"])
        summary["required_fields"] = names
    return summary


def inspect(case_path: Path) -> dict[str, Any]:
    with case_path.open(encoding="utf-8") as handle:
        case = json.load(handle)
    if not isinstance(case, dict):
        raise ValueError("case.json root must be an object")
    if "case_id" not in case:
        # Some wrappers nest the original case object; never manufacture an ID.
        case_id = find_key(case, "case_id")
    else:
        case_id = case["case_id"]
    if case_id is None or isinstance(case_id, (dict, list)):
        raise ValueError("case_id is missing or is not a scalar value")

    contract = case.get("output_contract")
    if contract is None:
        contract = find_key(case, "output_contract")

    input_root = case_path.parent
    pdfs = set(existing_pdf_strings(case, input_root))
    if input_root.is_dir():
        for path in input_root.rglob("*"):
            if path.is_file() and path.suffix.lower() == ".pdf":
                pdfs.add(str(path.resolve()))

    task_candidates = [input_root / "task.md", Path.cwd() / "task.md", Path("/input/task.md")]
    task_files = []
    seen = set()
    for path in task_candidates:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if str(resolved) not in seen and resolved.is_file():
            task_files.append(str(resolved))
            seen.add(str(resolved))

    return {
        "manifest_version": "pdf-parse-case-manifest@2.0.0",
        "case_path": str(case_path.resolve()),
        "case_id": case_id,
        "task_files": task_files,
        "pdf_files": sorted(pdfs),
        "output_contract": contract,
        "contract_summary": contract_summary(contract),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_json", type=Path)
    parser.add_argument("--output", type=Path, help="write manifest here; stdout remains a short summary")
    args = parser.parse_args()
    try:
        manifest = inspect(args.case_json)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(json.dumps({
        "status": "ok",
        "case_id": manifest["case_id"],
        "pdf_count": len(manifest["pdf_files"]),
        "required_fields": manifest["contract_summary"]["required_fields"],
        "allow_additional": manifest["contract_summary"]["allow_additional"],
        "output": str(args.output) if args.output else None,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
