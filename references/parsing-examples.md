# 最小调用与合成输出示例

> **本文件全部内容均为 synthetic（合成）接口示例，不对应任何正式案例，也不得复制到案例结果。** 示例只说明字段关系；实际执行必须读取当前 PDF。

## 1. 最小调用

```bash
python3 /skills/weekly-skill/scripts/inspect_case.py /input/case.json \
  --output /app/work/case_manifest.json
python3 /skills/weekly-skill/scripts/extract_pdf.py /input/ACTUAL.pdf /app/work/layout.json
# Agent 根据 task.md、output_contract、layout.json 和页图生成实际结果后：
python3 /skills/weekly-skill/scripts/validate_result.py /app/output/result.json \
  --case /input/case.json --layout /app/work/layout.json
```

`/input/ACTUAL.pdf` 是路径占位符，必须替换成 `case_manifest.json` 中实际存在的 PDF，不能原样执行。

## 2. 阅读顺序片段

合成首页包含通栏标题、通栏摘要、左栏两块、右栏两块。正确顺序是标题 → 摘要 → `LEFT_ONE` → `LEFT_TWO` → `RIGHT_ONE` → `RIGHT_TWO`，不是按物理行左右交替。

```json
{
  "paragraph_id": "P001",
  "text": "LEFT_ONE alpha",
  "section_id": "S1",
  "source_type": "text_layer",
  "locations": [
    {"pdf_page": 1, "printed_page": "1", "column": 1, "block": "p1-b003", "bbox": [50, 130, 130, 145]}
  ],
  "normalization": "none",
  "notes": "synthetic example"
}
```

`block` 与 `bbox` 仅演示格式；实际值必须来自布局证据。

## 3. 合并表头：`cells[]` 与 Markdown 必须一致

合成表格有两层表头：`Compound` 纵跨两行，`IC50 (μM)` 横跨两列。`cells[]` 只记录锚点：

```json
{
  "table_id": "T1",
  "caption": "Synthetic assay values",
  "locations": [
    {"pdf_page": 1, "printed_page": "1", "column": 0, "block": "p1-b010", "bbox": [40, 300, 560, 430]}
  ],
  "cells": [
    {"row": 1, "col": 1, "rowspan": 2, "colspan": 1, "text": "Compound", "is_header": true},
    {"row": 1, "col": 2, "rowspan": 1, "colspan": 2, "text": "IC50 (μM)", "is_header": true},
    {"row": 2, "col": 2, "rowspan": 1, "colspan": 1, "text": "K562", "is_header": true},
    {"row": 2, "col": 3, "rowspan": 1, "colspan": 1, "text": "HeLa", "is_header": true},
    {"row": 3, "col": 1, "rowspan": 1, "colspan": 1, "text": "X-01", "is_header": false},
    {"row": 3, "col": 2, "rowspan": 1, "colspan": 1, "text": "1.2", "is_header": false},
    {"row": 3, "col": 3, "rowspan": 1, "colspan": 1, "text": "3.4", "is_header": false},
    {"row": 4, "col": 1, "rowspan": 1, "colspan": 1, "text": "X-02", "is_header": false},
    {"row": 4, "col": 2, "rowspan": 1, "colspan": 1, "text": "5.6", "is_header": false},
    {"row": 4, "col": 3, "rowspan": 1, "colspan": 1, "text": "7.8", "is_header": false}
  ],
  "markdown": "| Compound | IC50 (μM) | IC50 (μM) |\n|:---|:---|:---|\n| Compound | K562 | HeLa |\n| X-01 | 1.2 | 3.4 |\n| X-02 | 5.6 | 7.8 |",
  "note": "synthetic；Markdown 为 cells 的展开网格，合并区域重复文字"
}
```

展开后的四行三列为：

```text
Compound   IC50 (μM)   IC50 (μM)
Compound   K562        HeLa
X-01       1.2         3.4
X-02       5.6         7.8
```

## 4. 公式与不确定 OCR

```json
{
  "formula_id": "EQ1",
  "number": "(1)",
  "latex": "\\Delta G = -RT \\ln K",
  "raw": "ΔG = −RT ln K",
  "locations": [
    {"pdf_page": 1, "printed_page": "1", "column": 2, "block": "p1-b014", "bbox": [330, 500, 450, 520]}
  ],
  "note": "synthetic；raw 保留提取形态，latex 为明确可核对的转写"
}
```

若 OCR 原文为 `IC5O` 且无法从页图确认最后一个字符，应保留 `raw_text="IC5O"` 并记 `ocr_uncertain`，不得根据常见缩写直接改成 `IC50`。任何纠正都必须同时记录改前、改后与依据。
