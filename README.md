# PDF 文献文档解析 Skill（pdf-parse@2.0.0）

面向科研 PDF 的“证据优先”解析工作流：先由确定性工具提取逐页文本块、坐标和候选阅读顺序，再由 Agent 结合页图完成章节、表格、公式、图注、参考文献等结构映射，最后用脚本检查输出契约、逐页覆盖、交叉引用、表格一致性和正文证据回溯。读不出的内容如实标注，不用模板或常识补齐。

## 文件结构

- `SKILL.md`：触发条件、Harbor 输入输出、七步流程、阅读顺序、表格/OCR 规则、状态判定与十二项硬检查。
- `scripts/inspect_case.py`：读取 `case_id`、PDF 清单及原始 `output_contract`，不生成答案。
- `scripts/extract_pdf.py`：调用 Poppler 生成带 SHA-256、文本块、坐标、候选栏序和页眉页脚候选的布局证据。
- `scripts/validate_result.py`：标准库校验器；支持实际案例契约和兜底 Schema。
- `references/result.schema.json`：契约缺失时使用的完整兜底结果模型。
- `references/parsing-examples.md`：最小调用及完全合成的段落、表格、公式示例。
- `references/exercise-set.md`：五类合成练习及可判定验收点。
- `references/test-report.md`：实际测试命令、结果和边界记录。
- `tests/`：单元测试、真实 PDF 集成测试及合成 PDF 生成器。

## 运行依赖

- 必需：Python 3（脚本仅使用标准库）。
- 坐标提取：Poppler `pdftotext`；可选渲染：Poppler `pdftoppm`。
- 运行镜像没有 Poppler 时，使用平台 `pdf-text-tool`、`pdf-render-tool`、`ocr-tool`，并在处理日志中记录实际方式。
- 可选开发依赖：`reportlab` 仅用于生成合成测试 PDF，不是正式运行依赖。

## 最小调用

```bash
export SKILL_DIR=/skills/weekly-skill
mkdir -p /app/work /app/output
python3 "$SKILL_DIR/scripts/inspect_case.py" /input/case.json \
  --output /app/work/case_manifest.json
python3 "$SKILL_DIR/scripts/extract_pdf.py" /input/ACTUAL.pdf /app/work/layout.json
# Agent 根据实际任务、契约、布局证据和页图生成 result.json 后：
python3 "$SKILL_DIR/scripts/validate_result.py" /app/output/result.json \
  --case /input/case.json --layout /app/work/layout.json
```

`ACTUAL.pdf` 必须替换为清单中的真实路径。多份 PDF 分别生成布局文件。`output_contract` 始终优先于兜底 Schema；严格契约禁止额外字段时不得添加扩展字段。

## 自测

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

测试覆盖 `case_id` 透传、严格契约、覆盖状态、ID 交叉引用、表格合并网格与 Markdown 一致性、OCR 修正记录、正文证据回溯，以及合成双栏 PDF 的阅读顺序和重复页眉识别。集成测试在没有 Poppler 或 `reportlab` 时会明确跳过，不伪报通过。

## 适用范围与限制

重点支持单栏、双栏及通栏混合块；三栏及以上、复杂嵌套表、数学语义和任意矢量图内部结构需要人工或专用工具复核。阅读顺序与页眉页脚标签是候选，必须结合页图确认。图表和公式只做结构提取，不解释科学含义。

本仓库对应北京化工大学高校分站赛第一期「阅读01｜文献文档解析」（challenge-id：`product-arena-08-3027d350`）。正式案例与白板由平台提供，本仓库不包含其预制答案。
