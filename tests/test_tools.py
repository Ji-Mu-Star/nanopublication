#!/usr/bin/env python3
"""Unit and integration tests for pdf-parse helper scripts (synthetic data only)."""
from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import extract_pdf  # noqa: E402
import inspect_case  # noqa: E402
import validate_result  # noqa: E402

SCHEMA = json.loads((ROOT / "references" / "result.schema.json").read_text(encoding="utf-8"))


def location() -> dict:
    return {"pdf_page": 1, "printed_page": "1", "column": 1, "block": "p1-b001", "bbox": [10, 10, 100, 30]}


def valid_result() -> dict:
    cells = [
        {"row": 1, "col": 1, "rowspan": 2, "colspan": 1, "text": "Compound", "is_header": True},
        {"row": 1, "col": 2, "rowspan": 1, "colspan": 2, "text": "IC50 (μM)", "is_header": True},
        {"row": 2, "col": 2, "rowspan": 1, "colspan": 1, "text": "K562", "is_header": True},
        {"row": 2, "col": 3, "rowspan": 1, "colspan": 1, "text": "HeLa", "is_header": True},
        {"row": 3, "col": 1, "rowspan": 1, "colspan": 1, "text": "X-01", "is_header": False},
        {"row": 3, "col": 2, "rowspan": 1, "colspan": 1, "text": "1.2", "is_header": False},
        {"row": 3, "col": 3, "rowspan": 1, "colspan": 1, "text": "3.4", "is_header": False},
        {"row": 4, "col": 1, "rowspan": 1, "colspan": 1, "text": "X-02", "is_header": False},
        {"row": 4, "col": 2, "rowspan": 1, "colspan": 1, "text": "5.6", "is_header": False},
        {"row": 4, "col": 3, "rowspan": 1, "colspan": 1, "text": "7.8", "is_header": False},
    ]
    markdown = (
        "| Compound | IC50 (μM) | IC50 (μM) |\n"
        "|:---|:---|:---|\n"
        "| Compound | K562 | HeLa |\n"
        "| X-01 | 1.2 | 3.4 |\n"
        "| X-02 | 5.6 | 7.8 |"
    )
    return {
        "case_id": "synthetic-case",
        "skill_version": "pdf-parse@2.0.0",
        "task_status": "success",
        "status_reason": "已处理 1 / 总 1 页；全部为合成测试内容",
        "sources": [{"path": "synthetic.pdf", "sha256": "0" * 64, "role": "source_pdf"}],
        "document": {
            "title": "Synthetic document", "authors": ["A. Example"],
            "affiliations": ["Synthetic Lab"], "abstract": "Synthetic abstract",
            "keywords": ["synthetic"], "document_id": None, "page_count": 1, "language": "en"
        },
        "sections": [{"section_id": "S1", "level": 1, "numbering": "1", "title": "Synthetic section",
                      "page_start": 1, "page_end": 1, "paragraph_ids": ["P001"]}],
        "paragraphs": [{"paragraph_id": "P001", "text": "Synthetic body text.", "section_id": "S1",
                        "source_type": "text_layer", "locations": [location()],
                        "normalization": "none", "notes": "synthetic"}],
        "tables": [{"table_id": "T1", "caption": "Synthetic table", "locations": [location()],
                    "markdown": markdown, "cells": cells, "note": "synthetic merged-header example"}],
        "figures": [], "formulas": [], "references": [], "footnotes": [], "headers_footers": [],
        "coverage": {"pages_total": 1, "pages_attempted": [1], "pages_completed": [1], "pages_failed": [], "notes": "synthetic"},
        "uncertain_items": [],
        "quality_check": {"overall_quality": "good", "issue_count": 0, "issues": [], "pass": True},
        "processing_log": [{"step": "validate", "status": "completed", "detail": "synthetic unit fixture"}],
    }


def layout_evidence(text: str = "Synthetic body text.") -> dict:
    return {
        "source_sha256": "0" * 64,
        "coverage_hint": {"pages_without_body_text": []},
        "pages": [{"pdf_page": 1, "reading_order": ["p1-b001"],
                   "blocks": [{"block_id": "p1-b001", "text": text}]}],
    }


class ValidatorTests(unittest.TestCase):
    def check(self, data, case=None, layout=None):
        return validate_result.validate(data, case, layout, SCHEMA)

    def test_valid_full_result(self):
        errors, warnings = self.check(valid_result(), layout=layout_evidence())
        self.assertEqual([], errors)
        self.assertEqual([], warnings)

    def test_case_id_must_pass_through(self):
        data = valid_result()
        errors, _ = self.check(data, case={"case_id": "different"})
        self.assertTrue(any("case_id" in error["path"] for error in errors))

    def test_strict_contract_rejects_extra_field(self):
        case = {"case_id": "c", "output_contract": {"type": "object", "required": ["case_id", "task_status"],
                "properties": {"case_id": {"type": "string"}, "task_status": {"type": "string"}},
                "additionalProperties": False}}
        errors, _ = self.check({"case_id": "c", "task_status": "partial", "extra": 1}, case=case)
        self.assertTrue(any("additional property" in error["issue"] for error in errors))

    def test_contract_required_field(self):
        case = {"case_id": "c", "output_contract": {"type": "object", "required": ["case_id", "answer"],
                "properties": {"case_id": {"type": "string"}, "answer": {"type": "string"}}}}
        errors, _ = self.check({"case_id": "c"}, case=case)
        self.assertTrue(any("answer" in error["issue"] for error in errors))

    def test_success_requires_complete_coverage(self):
        data = valid_result()
        data["coverage"]["pages_completed"] = []
        errors, _ = self.check(data)
        self.assertTrue(any("success requires every page" in error["issue"] for error in errors))

    def test_section_cross_reference(self):
        data = valid_result()
        data["sections"][0]["paragraph_ids"] = ["P999"]
        errors, _ = self.check(data)
        self.assertTrue(any("unknown paragraph" in error["issue"] for error in errors))

    def test_duplicate_id(self):
        data = valid_result()
        data["paragraphs"].append(copy.deepcopy(data["paragraphs"][0]))
        errors, _ = self.check(data)
        self.assertTrue(any("duplicate ID" in error["issue"] for error in errors))

    def test_table_markdown_must_match_cells(self):
        data = valid_result()
        data["tables"][0]["markdown"] = data["tables"][0]["markdown"].replace("| X-01 | 1.2 |", "| X-01 | 9.9 |")
        errors, _ = self.check(data)
        self.assertTrue(any("cell mismatch" in error["issue"] for error in errors))

    def test_table_grid_overlap(self):
        data = valid_result()
        data["tables"][0]["cells"].append({"row": 3, "col": 2, "rowspan": 1, "colspan": 1,
                                           "text": "overlap", "is_header": False})
        errors, _ = self.check(data)
        self.assertTrue(any("overlapping cell" in error["issue"] for error in errors))

    def test_template_text_fails_layout_provenance(self):
        errors, _ = self.check(valid_result(), layout=layout_evidence("Different source text."))
        self.assertTrue(any("not traceable" in error["issue"] for error in errors))

    def test_ocr_correction_needs_before_and_after(self):
        data = valid_result()
        data["task_status"] = "partial"
        data["quality_check"]["pass"] = False
        data["quality_check"]["issue_count"] = 1
        data["quality_check"]["issues"] = [{"issue_id": "Q001", "issue_type": "text_mismatch", "target_id": "P001",
                "issue_description": "synthetic", "correction_suggestion": "review", "detected_by": "script"}]
        data["uncertain_items"] = [{"item_id": "U001", "item_type": "ocr_corrected", "related_id": "P001",
                "description": "synthetic", "impact_level": "low", "suggestion": "review"}]
        errors, _ = self.check(data)
        self.assertTrue(any("raw_text and corrected_text" in error["issue"] for error in errors))


class LayoutAlgorithmTests(unittest.TestCase):
    def test_same_first_line_split_blocks_use_first_line_x(self):
        wide = {"block_id": "b2", "kind": "body", "column": 0, "order": None,
                "text": "Other Authors\nAffiliation\nlong-email",
                "bbox": [100, 130, 500, 170],
                "line_bboxes": [[200, 130, 500, 142], [200, 148, 400, 158], [100, 160, 490, 170]]}
        first_author = {"block_id": "b1", "kind": "body", "column": 0, "order": None,
                        "text": "First Author", "bbox": [121, 130, 190, 142],
                        "line_bboxes": [[121, 130, 190, 142]]}
        ordered, _ = extract_pdf.reading_order([wide, first_author], 600)
        self.assertEqual(["b1", "b2"], [block["block_id"] for block in ordered])

    def test_tall_narrow_side_block_is_margin_candidate(self):
        block = {"block_id": "p1-b001", "kind": "body", "text": "vertical source note",
                 "bbox": [18, 250, 36, 610]}
        page = {"pdf_page": 1, "width": 600, "height": 800, "blocks": [block]}
        candidates = extract_pdf.mark_margin_notes([page])
        self.assertEqual("margin_note_candidate", block["kind"])
        self.assertEqual("vertical source note", candidates[0]["text"])


class InspectCaseTests(unittest.TestCase):
    def test_manifest_preserves_case_id_and_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            case = {"case_id": 42, "output_contract": {"required": ["case_id"], "properties": {"case_id": {"type": "integer"}},
                    "additionalProperties": False}}
            path = root / "case.json"
            path.write_text(json.dumps(case), encoding="utf-8")
            manifest = inspect_case.inspect(path)
            self.assertEqual(42, manifest["case_id"])
            self.assertEqual(["case_id"], manifest["contract_summary"]["required_fields"])
            self.assertFalse(manifest["contract_summary"]["allow_additional"])


@unittest.skipUnless(shutil.which("pdftotext"), "Poppler pdftotext not installed")
class PdfIntegrationTests(unittest.TestCase):
    def test_synthetic_mixed_width_reading_order_and_header(self):
        try:
            from make_synthetic_pdf import make_pdf
        except ImportError:
            self.skipTest("reportlab is not installed (development-only integration dependency)")
        with tempfile.TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "synthetic.pdf"
            make_pdf(pdf_path)
            layout = extract_pdf.extract(pdf_path, timeout=60, render_dir=None)
            self.assertEqual(2, layout["page_count"])
            markers = ["Synthetic Reading Order Fixture", "ABSTRACT:", "LEFT_ONE", "LEFT_TWO", "RIGHT_ONE", "RIGHT_TWO"]
            positions = []
            page = layout["pages"][0]
            blocks = {block["block_id"]: block for block in page["blocks"]}
            for order, block_id in enumerate(page["reading_order"]):
                text = blocks[block_id]["text"]
                for marker in markers:
                    offset = text.find(marker)
                    if offset >= 0:
                        positions.append((order, offset, marker))
            observed = [item[2] for item in sorted(positions)]
            self.assertEqual(markers, observed)
            second = layout["pages"][1]
            ordered_second = [block for block in sorted(second["blocks"], key=lambda b: b["order"] or 999)
                              if block.get("kind") == "body"]
            second_text = "\n".join(block["text"] for block in ordered_second)
            self.assertLess(second_text.find("LEFT_THREE"), second_text.find("RIGHT_THREE"))
            repeated = layout["headers_footers_candidates"]
            self.assertTrue(any(item["text"] == "SYNTHETIC HEADER" and item["pages"] == [1, 2] for item in repeated))


if __name__ == "__main__":
    unittest.main(verbosity=2)
