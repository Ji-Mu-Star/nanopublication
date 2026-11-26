#!/usr/bin/env python3
"""Lightweight structural validator for the Nanopublication result.json.

Only the standard library (json) is used, so it runs anywhere Python 3 is
present. It is a *key-field manual check*, not a full jsonschema validation:
it checks required top-level keys, controlled-vocabulary enum values, ID
patterns, and the internal cross-consistency that the SKILL.md section 9
checklist requires. It never invents a value and never modifies the file.

Usage:
    python3 validate_result.py /app/output/result.json [output_schema.json]

Exit code:
    0  -> no violations found
    1  -> violations found (printed to stdout, one per line as JSON objects)
"""
from __future__ import annotations

import json
import re
import sys

TASK_STATUS = {"success", "partial", "failed"}
ASSERTION_TYPE = {"fact_statement", "experiment_result", "conclusion_inference", "method_description"}
CERTAINTY = {"confirmed", "conditional", "uncertain"}
EVIDENCE_TYPE = {"text_evidence", "figure_evidence", "table_evidence"}
SUPPORT_RELATION = {"direct_support", "partial_support", "indirect_inference"}
IMPACT_LEVEL = {"high", "medium", "low"}
LOG_STATUS = {"completed", "partial", "failed"}
DOCUMENT_TYPE = {"journal_article", "conference_paper", "preprint", "thesis", "book_chapter", "other"}
SOURCE_SECTION = {"abstract", "introduction", "methods", "results", "discussion", "conclusion", "other"}
QUALITY = {"excellent", "good", "fair", "poor"}
ISSUE_TYPES = {
    "granularity_too_coarse", "granularity_too_fine", "faithfulness_violation",
    "evidence_mismatch", "evidence_insufficient", "relation_type_wrong",
    "direction_reversed", "subject_confusion", "location_missing",
    "metadata_missing", "format_invalid", "duplicate_assertion",
}
TOP_REQUIRED = [
    "case_id", "task_status", "status_reason", "answer", "source_metadata",
    "assertions", "quality_check", "uncertainty_items", "processing_log",
    "skill_version",
]
ASSERTION_REQUIRED = [
    "assertion_id", "assertion_text", "assertion_type", "certainty", "scope",
    "confidence_score", "confidence_rationale", "evidence", "notes",
]
EVIDENCE_REQUIRED = ["evidence_id", "evidence_text", "evidence_type", "support_relation", "location"]
LOCATION_REQUIRED = ["page", "paragraph_index", "sentence_index"]
UNCERTAINTY_REQUIRED = ["item_id", "item_type", "related_assertion_id", "description", "impact_level", "suggestion"]
LOG_REQUIRED = ["step", "status", "detail"]

ID_RE = re.compile(r"^A[0-9]{3}$")
EVID_ID_RE = re.compile(r"^A[0-9]{3}-E[0-9]+$")
UNC_ID_RE = re.compile(r"^U[0-9]{3}$")
ISSUE_ID_RE = re.compile(r"^Q[0-9]{3}$")


def violations_for(data: object) -> list[dict]:
    v: list[dict] = []
    if not isinstance(data, dict):
        return [{"path": "$", "issue": "root must be a JSON object"}]

    def add(path: str, issue: str) -> None:
        v.append({"path": path, "issue": issue})

    for key in TOP_REQUIRED:
        if key not in data:
            add("$", f"missing required top-level key: {key}")

    if data.get("task_status") not in TASK_STATUS:
        add("$.task_status", f"value {data.get('task_status')!r} not in {sorted(TASK_STATUS)}")

    # answer
    answer = data.get("answer")
    if isinstance(answer, dict):
        for key in ("question", "direct_answer", "answer_assertion_ids"):
            if key not in answer:
                add("$.answer", f"missing required key: {key}")
    else:
        add("$.answer", "answer must be an object")

    # assertions
    assertions = data.get("assertions")
    if not isinstance(assertions, list):
        add("$.assertions", "assertions must be an array")
    else:
        seen_ids: set[str] = set()
        for i, a in enumerate(assertions):
            p = f"$.assertions[{i}]"
            if not isinstance(a, dict):
                add(p, "assertion must be an object")
                continue
            for key in ASSERTION_REQUIRED:
                if key not in a:
                    add(p, f"missing required key: {key}")
            aid = a.get("assertion_id")
            if not isinstance(aid, str) or not ID_RE.match(aid):
                add(f"{p}.assertion_id", f"{aid!r} does not match ^A[0-9]{{3}}$")
            elif aid in seen_ids:
                add(f"{p}.assertion_id", f"duplicate assertion id {aid}")
            seen_ids.add(str(aid))
            if a.get("assertion_type") not in ASSERTION_TYPE:
                add(f"{p}.assertion_type", f"{a.get('assertion_type')!r} not in controlled vocabulary")
            if a.get("certainty") not in CERTAINTY:
                add(f"{p}.certainty", f"{a.get('certainty')!r} not in controlled vocabulary")
            cs = a.get("confidence_score")
            if not isinstance(cs, (int, float)) or isinstance(cs, bool) or not (0.0 <= cs <= 1.0):
                add(f"{p}.confidence_score", f"{cs!r} must be a number in [0,1]")
            evidence = a.get("evidence")
            if not isinstance(evidence, list):
                add(f"{p}.evidence", "evidence must be an array")
            else:
                for j, e in enumerate(evidence):
                    ep = f"{p}.evidence[{j}]"
                    if not isinstance(e, dict):
                        add(ep, "evidence item must be an object")
                        continue
                    for key in EVIDENCE_REQUIRED:
                        if key not in e:
                            add(ep, f"missing required key: {key}")
                    eid = e.get("evidence_id")
                    if not isinstance(eid, str) or not EVID_ID_RE.match(eid):
                        add(f"{ep}.evidence_id", f"{eid!r} does not match ^A[0-9]{{3}}-E[0-9]+$")
                    if e.get("evidence_type") not in EVIDENCE_TYPE:
                        add(f"{ep}.evidence_type", f"{e.get('evidence_type')!r} not in controlled vocabulary")
                    if e.get("support_relation") not in SUPPORT_RELATION:
                        add(f"{ep}.support_relation", f"{e.get('support_relation')!r} not in controlled vocabulary")
                    loc = e.get("location")
                    if not isinstance(loc, dict):
                        add(f"{ep}.location", "location must be an object")
                    else:
                        for key in LOCATION_REQUIRED:
                            if key not in loc:
                                add(f"{ep}.location", f"missing required key: {key}")

    # source_metadata
    sm = data.get("source_metadata")
    if isinstance(sm, dict):
        for key in ("document_title", "document_id", "document_type", "authors",
                    "publish_year", "publish_source", "version", "source_page_range",
                    "source_section", "source_paragraph_range", "metadata_notes"):
            if key not in sm:
                add("$.source_metadata", f"missing required key: {key}")
        if sm.get("document_type") not in DOCUMENT_TYPE:
            add("$.source_metadata.document_type", f"{sm.get('document_type')!r} not in controlled vocabulary")
        if sm.get("source_section") not in SOURCE_SECTION:
            add("$.source_metadata.source_section", f"{sm.get('source_section')!r} not in controlled vocabulary")
    else:
        add("$.source_metadata", "source_metadata must be an object")

    # quality_check
    qc = data.get("quality_check")
    if isinstance(qc, dict):
        for key in ("overall_quality", "issue_count", "issues", "pass"):
            if key not in qc:
                add("$.quality_check", f"missing required key: {key}")
        if qc.get("overall_quality") not in QUALITY:
            add("$.quality_check.overall_quality", f"{qc.get('overall_quality')!r} not in controlled vocabulary")
        issues = qc.get("issues")
        if isinstance(issues, list) and isinstance(qc.get("issue_count"), (int, float)):
            if int(qc["issue_count"]) != len(issues):
                add("$.quality_check", f"issue_count ({qc['issue_count']}) != len(issues) ({len(issues)})")
        if isinstance(issues, list):
            for k, it in enumerate(issues):
                if isinstance(it, dict) and it.get("issue_type") not in ISSUE_TYPES:
                    add(f"$.quality_check.issues[{k}].issue_type", f"{it.get('issue_type')!r} not in controlled vocabulary")

    # uncertainty_items
    unc = data.get("uncertainty_items")
    if isinstance(unc, list):
        for i, u in enumerate(unc):
            p = f"$.uncertainty_items[{i}]"
            if not isinstance(u, dict):
                add(p, "item must be an object")
                continue
            for key in UNCERTAINTY_REQUIRED:
                if key not in u:
                    add(p, f"missing required key: {key}")
            if isinstance(u.get("item_id"), str) and not UNC_ID_RE.match(u["item_id"]):
                add(f"{p}.item_id", f"{u.get('item_id')!r} does not match ^U[0-9]{{3}}$")
            if u.get("impact_level") not in IMPACT_LEVEL:
                add(f"{p}.impact_level", f"{u.get('impact_level')!r} not in controlled vocabulary")

    # processing_log
    log = data.get("processing_log")
    if isinstance(log, list):
        for i, step in enumerate(log):
            p = f"$.processing_log[{i}]"
            if not isinstance(step, dict):
                add(p, "step must be an object")
                continue
            for key in LOG_REQUIRED:
                if key not in step:
                    add(p, f"missing required key: {key}")
            if step.get("status") not in LOG_STATUS:
                add(f"{p}.status", f"{step.get('status')!r} not in controlled vocabulary")

    # answer_assertion_ids must reference existing assertions
    if isinstance(answer, dict) and isinstance(answer.get("answer_assertion_ids"), list):
        valid_ids = set()
        if isinstance(assertions, list):
            for a in assertions:
                if isinstance(a, dict) and isinstance(a.get("assertion_id"), str):
                    valid_ids.add(a["assertion_id"])
        for rid in answer["answer_assertion_ids"]:
            if rid not in valid_ids:
                add("$.answer.answer_assertion_ids", f"{rid!r} does not reference an existing assertion")

    return v


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: validate_result.py RESULT.json [SCHEMA.json]", file=sys.stderr)
        return 2
    result_path = argv[0]
    try:
        with open(result_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        print(f'{{"path": "{result_path}", "issue": "file not found"}}')
        return 1
    except json.JSONDecodeError as exc:
        print(f'{{"path": "{result_path}", "issue": "invalid JSON: {exc}"}}')
        return 1

    violations = violations_for(data)
    if violations:
        for item in violations:
            print(json.dumps(item, ensure_ascii=False))
        print(f"validation failed: {len(violations)} violation(s)", file=sys.stderr)
        return 1
    print("validation passed: no violations found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
