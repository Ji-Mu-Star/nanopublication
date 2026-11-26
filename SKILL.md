---
name: nanopublication
description: 科研阅读与 Nanopublication 结构化 Skill。把科研论文段落拆解为单一可独立判断真假的细粒度断言，为每条断言绑定原文最小充分证据片段及页码/段落/句子级位置，补全论文-作者-年份-版本溯源元数据，输出可直接被下游程序解析的 JSON。当任务涉及科研论文阅读问答并给出依据、断言拆解（assertion splitting）、证据绑定（evidence binding）、Nanopublication 生成、assertion verification、科研知识结构化导出、论文结论溯源复核时使用。
---

# Nanopublication：科研阅读，回答问题，也给出依据

## 0. 一句话说明

输入一段真实科研论文文本 + 任务问题，本 Skill 输出一份「每条断言都能回到原文某句、每个来源字段都能追溯到论文」的结构化 JSON：拆得细、对得上、追得回、读得懂。

**核心纪律：所有断言与证据 100% 来自输入材料。禁止补充外部知识，禁止主观推论，禁止改写原意，禁止把整段话塞进一个"断言"字段。**

---

## 0.1 执行前必读（Agent 进入后第一步，逐条执行，不可跳过）

1. 先读 `/input/case.json`，提取 `case_id`、任务要求、材料路径、来源上下文与 `output_contract`（若提供）。`case_id` 必须原样透传到输出。
2. 再读任务说明文件 `task.md`（优先 `/input/task.md`；不存在则读当前工作目录的 `task.md`，或 `case.json` 内嵌任务字段）。
3. 用平台 PDF 工具读真实 PDF 正文：优先 `pdf-text-tool` 提取文本层；无文本层或乱码时用 `ocr-tool`，必要时用 `pdf-render-tool` 辅助核查。**禁止**凭文件名或标签假设正文内容，**禁止**只读预抽取文本。
4. 确认输出：`/app/output/result.json` 必须包含平台 `output_contract` 全部原始字段 + `case_id` + `skill_version`；人读版写 `/app/output/result.md`。
5. 然后按第 3 节七步流程执行；预算内先落盘合法 JSON，再增量补全。

---

## 1. 适用条件（何时用、何时不用）

### 1.1 应当触发本 Skill 的输入特征

- 输入为科研论文正文（摘要 / 结果 / 讨论 / 方法 / 结论任一段落），并带有"回答问题、给出依据""拆成断言""标注出处""结构化导出"类要求；
- 输入为 PDF / 纯文本论文材料，需要产出可复核的知识单元；
- 需要把已有结论转成可机器读取的结构（知识图谱前置、断言库、证据表）；
- 需要校验某条结论是否有原文支撑、支撑到什么程度。

### 1.2 不适用，应直接说明边界并拒答具体子任务

| 不适用情形 | 处置 |
|---|---|
| 纯扫描版 PDF，无文本层、无 OCR 结果 | 先尝试平台 `ocr-tool`；仍不可读则声明无法读取正文，`task_status=failed`；不猜测内容 |
| 输入根本不是学术文本（新闻、科普、营销稿、聊天记录） | 说明不适用，可提示改用普通摘要能力 |
| 要求判断论文结论在科学上是否成立 / 是否有学术争议 | 超出范围：本 Skill 只做"原文说了什么 + 原文哪里说了"，不做真伪评判 |
| 要求补全原文未提及的背景、机制、数据 | 拒绝补造；在 `uncertainty_items` 记 `out_of_scope` |
| 要求整本期刊 / 数百页批量无差别抽取 | 说明按段落级优化，建议分批；不得声称已覆盖全文 |
| 要求读取图表内部数据点（像素级曲线取值） | 只能提取正文中**文字陈述**的图表结论，并在 `evidence_type` 标 `figure_evidence` / `table_evidence`、`notes` 说明未读取原始数据 |

### 1.3 允许不完整

任务只要求"回答问题"时，仍必须输出完整结构；`assertions` 可为空但 `uncertainty_items`、`status_reason` 必须说明原因。

---

## 2. 安装与调用

### 2.1 文件与目录

```
submission/                  # 提交目录根（即 /app/submission/；平台把 Skill 安装到 /skills/weekly-skill/）
├── SKILL.md                 # 本文件（入口，必须存在；frontmatter 的 name/description 必须合法）
├── GITHUB_URL.txt           # 第一行 GitHub 链接；第二行可选相对文件路径
├── references/
│   ├── assertion-examples.md  # 20 条断言样例（可复用标注规范，见 2.6）
│   └── exercise-set.md        # 3 组练习段落（拆解提示，见 2.6）
└── scripts/
    └── validate_result.py     # 可选：result.json 结构自检（仅标准库 json，见第 9 节）
```

本 Skill 为纯提示 + 规则型 Skill，**不依赖任何第三方库、不依赖 Python 环境、不依赖外部 API**。可选增强（不影响主流程）：

- 若运行环境有 `python3`，可用 `scripts/validate_result.py` 对输出做结构自检（见第 9 节）；
- 无 Python 时，人工按第 9 节清单自查即可，视为同等有效。

### 2.2 平台运行时输入（Harbor 契约）

| 路径 | 内容 |
|---|---|
| `/input/case.json` | 案例结构化输入，含案例 ID、任务说明、材料路径、来源上下文与 `output_contract`（若提供） |
| `task.md` | 任务说明与具体问题。优先读 `/input/task.md`；若不存在，读当前工作目录下的 `task.md`，或 `case.json` 内嵌任务字段 |
| 附件 PDF | 平台直接给出真实 PDF，**无预抽取答案层**。用 `pdf-text-tool` 提取文本层；无文本层/乱码时用 `ocr-tool`，必要时 `pdf-render-tool` 辅助核查。禁止凭文件名或标签假设正文内容 |

### 2.3 平台运行时输出

写入 `/app/output/result.json`（提交目录是 `/app/submission/`，工作目录是 `/app/work`）：

- `case_id` **必须原样透传** `/input/case.json` 的案例标识，不得改写、不得省略；
- 必须包含平台 `output_contract` 要求的**全部原始字段**（字段名原样保留，不得改名）；
- 本文件第 7 节字段为本 Skill 的推荐完整集；若平台契约字段更少，只可**增加**不可**删减**；
- 若平台 Schema 声明 `additionalProperties: false`，把 `spo`、`confidence_score`、`confidence_rationale`、`quality_check`、`processing_log` 等扩展字段整体收进 `ext` 对象，核心字段不变；
- `skill_version` 固定为 `"nanopublication@1.0.0"`；
- 同时把可读版结果写 `/app/output/result.md`（人读复核用），二者内容必须一致。

### 2.4 手工/对话调用格式

```
【任务类型】Nanopublication 断言拆解与证据绑定
【案例ID】case-xxx
【问题】本次需要回答或抽取的具体问题（可为空，为空则默认抽取全部关键结论）
【科研文本】
（粘贴原文，段落之间空一行；若来自 PDF，请标注每段所属页码）
【来源上下文】
论文标题：xxx
DOI / PMID / arXiv：xxx
作者：A, B, C
发表年份：2024
期刊/会议/出版社：xxx
版本：预印本 v1 / 正式发表版
页码范围：第 3-5 页
所属章节：results
```

### 2.5 最小可运行调用（示例，非正式案例结果）

**输入**

```
【案例ID】sample-001
【问题】化合物 A 对 HepG2 细胞活力有什么影响，依据是什么？
【科研文本】
（第 3 页，results 第 1 段）在 25℃、1 atm 条件下，采用 MTT 法检测细胞活力。结果显示，浓度为 10 μmol/L 的化合物 A 处理 24 h 后，HepG2 细胞存活率降至 42.3%（p < 0.05），且细胞凋亡率显著升高。该结果表明化合物 A 具有抑制肝癌细胞增殖的潜在活性。
【来源上下文】
论文标题：化合物 A 的抗肿瘤活性研究
发表年份：2024
页码范围：第 3 页
所属章节：results
```

**输出（节选，示例）**

```json
{
  "case_id": "sample-001",
  "skill_version": "nanopublication@1.0.0",
  "task_status": "success",
  "status_reason": "处理完成，无异常",
  "answer": {
    "question": "化合物 A 对 HepG2 细胞活力有什么影响，依据是什么？",
    "direct_answer": "10 μmol/L 化合物 A 处理 24 h 后使 HepG2 细胞存活率降至 42.3%（p < 0.05），细胞凋亡率显著升高；作者据此推断其具有抑制肝癌细胞增殖的潜在活性。",
    "answer_assertion_ids": ["A002", "A003", "A004"],
    "answer_caveats": "结论为作者基于单一细胞系的体外实验推断，原文未报告体内验证。"
  },
  "source_metadata": {
    "document_title": "化合物 A 的抗肿瘤活性研究",
    "document_id": null,
    "document_type": "journal_article",
    "authors": [],
    "publish_year": 2024,
    "publish_source": "",
    "version": "",
    "source_page_range": [3],
    "source_section": "results",
    "source_paragraph_range": [1],
    "metadata_notes": "输入未提供 DOI、作者与期刊名，相应字段置 null，未作推断。"
  },
  "assertions": [
    {
      "assertion_id": "A001",
      "assertion_text": "本实验在 25℃、1 atm 条件下采用 MTT 法检测细胞活力。",
      "assertion_type": "method_description",
      "certainty": "confirmed",
      "scope": "仅适用于该实验条件：25℃、1 atm；检测对象为细胞活力。",
      "spo": { "subject": "本实验", "predicate": "采用", "object": "MTT 法检测细胞活力" },
      "confidence_score": 0.9,
      "confidence_rationale": "原文直接陈述方法，无保留语气，direct_support。",
      "evidence": [
        {
          "evidence_id": "A001-E1",
          "evidence_text": "在 25℃、1 atm 条件下，采用 MTT 法检测细胞活力。",
          "evidence_type": "text_evidence",
          "support_relation": "direct_support",
          "location": {
            "page": 3, "paragraph_index": 1, "sentence_index": 1,
            "char_span": [], "figure_table_id": null
          }
        }
      ],
      "notes": ""
    },
    {
      "assertion_id": "A002",
      "assertion_text": "10 μmol/L 化合物 A 处理 HepG2 细胞 24 h 后，细胞存活率降至 42.3%。",
      "assertion_type": "experiment_result",
      "certainty": "confirmed",
      "scope": "化合物 A 浓度 10 μmol/L；处理时长 24 h；细胞系 HepG2；对照组未在本文片段中说明。",
      "spo": { "subject": "10 μmol/L 化合物 A 处理 24 h 的 HepG2 细胞", "predicate": "细胞存活率降至", "object": "42.3%" },
      "confidence_score": 0.9,
      "confidence_rationale": "数值与条件在同一句中完整陈述，direct_support。",
      "evidence": [
        {
          "evidence_id": "A002-E1",
          "evidence_text": "浓度为 10 μmol/L 的化合物 A 处理 24 h 后，HepG2 细胞存活率降至 42.3%",
          "evidence_type": "text_evidence",
          "support_relation": "direct_support",
          "location": {
            "page": 3, "paragraph_index": 1, "sentence_index": 2,
            "char_span": [], "figure_table_id": null
          }
        }
      ],
      "notes": "原文同一句给出 p < 0.05，统计限定已单独拆为 A003。"
    },
    {
      "assertion_id": "A003",
      "assertion_text": "上述存活率下降在原报告中达到统计显著（p < 0.05）。",
      "assertion_type": "experiment_result",
      "certainty": "confirmed",
      "scope": "显著性水平 p < 0.05；仅对应 A002 所述比较。",
      "spo": { "subject": "A002 所述存活率下降", "predicate": "统计显著性为", "object": "p < 0.05" },
      "confidence_score": 0.9,
      "confidence_rationale": "原文括注给出显著性水平，direct_support。",
      "evidence": [
        {
          "evidence_id": "A003-E1",
          "evidence_text": "（p < 0.05）",
          "evidence_type": "text_evidence",
          "support_relation": "direct_support",
          "location": {
            "page": 3, "paragraph_index": 1, "sentence_index": 2,
            "char_span": [], "figure_table_id": null
          }
        }
      ],
      "notes": "原文未说明所用统计检验方法，故不新增该断言。"
    },
    {
      "assertion_id": "A004",
      "assertion_text": "10 μmol/L 化合物 A 处理 24 h 后 HepG2 细胞凋亡率较对照升高。",
      "assertion_type": "experiment_result",
      "certainty": "confirmed",
      "scope": "浓度与时长同上；原文仅表述为“显著升高”，未给出具体数值与对照定义。",
      "spo": { "subject": "10 μmol/L 化合物 A 处理 24 h 的 HepG2 细胞", "predicate": "细胞凋亡率升高", "object": "（相对对照，具体数值未报告）" },
      "confidence_score": 0.8,
      "confidence_rationale": "原文明确陈述升高，但缺少数值与对照基准，证据不完整。",
      "evidence": [
        {
          "evidence_id": "A004-E1",
          "evidence_text": "且细胞凋亡率显著升高",
          "evidence_type": "text_evidence",
          "support_relation": "partial_support",
          "location": {
            "page": 3, "paragraph_index": 1, "sentence_index": 2,
            "char_span": [], "figure_table_id": null
          }
        }
      ],
      "notes": "“显著”是否伴随统计检验原文未说明，数值缺失。"
    },
    {
      "assertion_id": "A005",
      "assertion_text": "作者认为化合物 A 具有抑制肝癌细胞增殖的潜在活性。",
      "assertion_type": "conclusion_inference",
      "certainty": "uncertain",
      "scope": "作者基于 HepG2 单细胞系体外实验的推断，原文措辞为“潜在活性”。",
      "spo": { "subject": "化合物 A", "predicate": "作者推断其具有", "object": "抑制肝癌细胞增殖的潜在活性" },
      "confidence_score": 0.6,
      "confidence_rationale": "断言的归属主体是“作者推断”，而非实验证实；indirect_inference。",
      "evidence": [
        {
          "evidence_id": "A005-E1",
          "evidence_text": "该结果表明化合物 A 具有抑制肝癌细胞增殖的潜在活性。",
          "evidence_type": "text_evidence",
          "support_relation": "indirect_inference",
          "location": {
            "page": 3, "paragraph_index": 1, "sentence_index": 3,
            "char_span": [], "figure_table_id": null
          }
        }
      ],
      "notes": "原文未区分“抑制增殖”与“细胞毒杀伤”，本 Skill 不代为判定，故 strict 表述为“作者认为”。"
    }
  ],
  "quality_check": {
    "overall_quality": "good",
    "issue_count": 0,
    "issues": [],
    "pass": true
  },
  "uncertainty_items": [
    {
      "item_id": "U001",
      "item_type": "unreported_data",
      "related_assertion_id": "A004",
      "description": "细胞凋亡率仅表述为“显著升高”，未报告具体百分比、检测方法与统计检验。",
      "impact_level": "medium",
      "suggestion": "回原文补充结果章节或补充材料；若原文确无，保持 partial_support 不得升级为定量结论。"
    },
    {
      "item_id": "U002",
      "item_type": "missing_metadata",
      "related_assertion_id": null,
      "description": "输入未提供 DOI、作者名单与期刊名，无法完成去重与版本核对。",
      "impact_level": "low",
      "suggestion": "向用户索取首页信息或 DOI，补齐 source_metadata 后重跑。"
    }
  ],
  "processing_log": [
    { "step": "1_input_parse", "timestamp": "", "status": "completed", "detail": "识别为 results 章节单段落，页码 3，1 段 3 句。" },
    { "step": "2_metadata_extract", "timestamp": "", "status": "completed", "detail": "标题、年份、页码、章节取自输入；DOI/作者缺失置 null。" },
    { "step": "3_assertion_split", "timestamp": "", "status": "completed", "detail": "拆出 5 条断言：方法 1、结果 3、推论 1。" },
    { "step": "4_evidence_bind", "timestamp": "", "status": "completed", "detail": "5 条全部绑定文本证据，逐字摘抄，位置到句级。" },
    { "step": "5_quality_check", "timestamp": "", "status": "completed", "detail": "10 项检查通过；A004 标 partial_support。" },
    { "step": "6_uncertainty", "timestamp": "", "status": "completed", "detail": "记录 2 项：未报告数据、元数据缺失。" },
    { "step": "7_output", "timestamp": "", "status": "completed", "detail": "输出 result.json 与 result.md。" }
  ]
}
```

> 以上为接口与流程示意，**不是正式案例结果**，不得当作测试答案复用。

### 2.6 可复用样例与题集

- `references/assertion-examples.md`：20 条断言样例，覆盖四类断言、三类确定性、三类支撑关系、三类证据类型，以及并列/因果/多数值/指代还原/未报告/图表证据/冲突等边界情形，并附"规则覆盖速查"。
- `references/exercise-set.md`：3 组练习段落（含拆解提示，不做预制标准答案），供标注培训与能力测试。

标注人员可据此复核，避免凭语感判断粒度与证据充分性。

---

## 3. 处理流程（7 步，顺序固定）

以下七步为执行主路径；第 4–8 节是步骤 3–5 的详细判据与字段字典，**按需查阅对应小节即可，不必逐字复述**。执行时以"读输入→拆断言→绑证据→自检→答题→落盘"为主线。

### 步骤 1：输入解析与边界识别

1. 读 `/input/case.json` 提取 `case_id`、问题、材料路径、来源上下文与 `output_contract`（若提供）；再读 `task.md`（先 `/input/task.md`，缺失则工作目录兜底，见 2.2）。
2. 若是 PDF：优先 `pdf-text-tool` 按页读正文；无文本层/乱码用 `ocr-tool`，必要时 `pdf-render-tool` 辅助核查；记录每段起始页码；跳过参考文献列表（除非任务要求）。
3. 判定可用性：是否有可读文本层、是否学术文本、问题是否落在材料范围内。
4. 任一不可用 → 直接置 `task_status = "failed"`，写清 `status_reason`，**不要凑答案**。

### 步骤 2：来源元数据提取

1. 优先取输入显式给定字段；其次取论文首页、页眉页脚、DOI 行。
2. 取不到的字段填 `null`（字符串型填 `""`），在 `metadata_notes` 说明缺失。
3. 多来源冲突（如输入年份与首页不符）→ 两个值都记录，`metadata_notes` 标 `conflict`，并在 `uncertainty_items` 记一条。

### 步骤 3：细粒度断言拆解

按第 4 节规则执行，产出 `assertions[]`。

### 步骤 4：证据绑定与位置标注

按第 5 节规则执行，为每条断言填 `evidence[]`。

### 步骤 5：质量自检与修正

按第 9 节 10 项清单逐条过，发现即修；修不了 → 记 `quality_check.issues` + `uncertainty_items`。

### 步骤 6：回答问题并给依据

把 `answer` 字段写满：

- `direct_answer`：只用 `assertions` 里已有的断言组织，不得引入新内容；
- `answer_assertion_ids`：回答所依赖的断言 ID 列表（必须真实存在）；
- `answer_caveats`：结论成立条件、未报告项、间接证据。

### 步骤 7：结构化输出

先写 `result.json`（严格 JSON，无注释无尾逗号），再写 `result.md`（同内容的人读版），最后按第 9 节清单终检。

---

## 4. 断言拆解规则

### 4.1 原子性判据（可操作，不靠语感）

一条断言合格，当且仅当同时通过以下四测：

| 判据 | 测验方法 | 不合格表现 |
|---|---|---|
| **否定单值测试** | 对断言整体取反，只应得到**一个**明确对立命题 | 取反后出现"多个不同地方可能错"，说明含多个命题 |
| **独立真假测试** | 断言的一部分为假、另一部分为真时，是否可能 | 可能 → 必须拆开 |
| **连接词测试** | 是否由"并且/同时/此外/以及/不仅…而且/因此/导致/然而/尽管/从而"串联 | 有 → 按连接词切开，各成一条 |
| **限定归属测试** | 每条断言的限定条件是否只作用于它自己 | 一个限定同时管两个结论 → 拆开并各自带上限定 |

### 4.2 强制的拆分动作

| 原文结构 | 拆法 |
|---|---|
| 并列（并且、同时、此外、以及、一方面…另一方面） | 每个并列项一条断言 |
| 因果（因此、导致、使得、由于、从而） | 原因一条、结果一条，"作者据此推断"再一条（`conclusion_inference`） |
| 转折（然而、但是、尽管、虽然） | 转折前后各一条 |
| 递进（不仅…而且、进一步） | 逐级各一条 |
| 一句话含多组数值 | 每组"对象+数值+条件"一条（如浓度、p 值、剂量分开） |
| 结论句含"提示/表明/暗示" | 主体改为"作者认为/作者推断"，`certainty=uncertain`，`assertion_type=conclusion_inference` |

### 4.3 必须保留的限定（进 `scope`，不得丢）

- 实验条件：温度、压力、pH、培养基、光照/湿度
- 样本与对象：物种、品系、细胞系、样本量 n、分组与对照定义
- 干预参数：浓度/剂量、给药途径、处理时长、随访期
- 统计限定：显著性水平、检验方法、置信区间、效应量、多重比较校正
- 适用范围：人群/地域/时间窗/设备型号/软件版本/模型假设
- 措辞限定：可能、提示、初步、in vitro、in vivo、preclinical

### 4.4 断言类型受控词表（4 值，不得自造）

| 值 | 定义 | 典型触发 |
|---|---|---|
| `fact_statement` | 客观事实、背景、已确立常识 | "已知""已有研究表明"（须注意：这是转述他人工作，不是本文结果） |
| `experiment_result` | 本文观测/测量/统计结果 | 出现数值、显著性或图表陈述 |
| `conclusion_inference` | 作者推论、机制解释、意义判断 | "提示""表明""我们认为""可能机制" |
| `method_description` | 方法、流程、材料、方案 | "采用""按照""使用…法" |

### 4.5 确定性受控词表（3 值）

| 值 | 判据 |
|---|---|
| `confirmed` | 原文肯定直陈，无保留词 |
| `conditional` | 带前提/条件从句，条件满足才成立 |
| `uncertain` | 含可能、或许、提示、初步、有待验证、潜在 |

### 4.6 禁止事项（命中即判定输出不合格）

1. 把整段或整句直接当一条断言；
2. 概括、提炼、升华原文（如把"存活率降至 42.3%"写成"显著抑制增殖"）；
3. 同义替换关键术语（如把"存活率"换成"细胞数量"）；
4. 删除限定扩大适用范围（如把"in vitro"删掉）；
5. 引入原文没有的机制、背景、比较对象；
6. 把他人文献结论写成本文结果（`fact_statement` 时须在 `scope` 标"转述他文，非本文实验"）；
7. 一条断言挂两组互相独立的数值。

---

## 5. 证据绑定规则

### 5.1 最小充分性判据（删减测试）

对候选证据片段依次做两件事：

1. **删减测试**：尝试删去片段中任一分句、修饰语、括注。若删后**仍能**独立支撑该断言 → 说明原片段不最小，继续删；若删后**不能**支撑 → 保留该成分，即当前为最小。
2. **缺口测试**：断言里的每个限定（条件、数值、n、p 值、范围）在证据片段中是否都能找到对应文字。缺一项 → 该证据只算 `partial_support`，并在 `notes` 写明缺什么。

允许的最小粒度下限：一个能独立成立的**分句或带括注的数值短语**。截断处不得造成语义反转或指代悬空（出现"该方法""上述处理"等指代时，须把指代对象的最小先行词一并纳入）。

### 5.2 原文保真

- `evidence_text` 必须逐字复制，**不得**改标点、改语序、删限定词、翻译；
- 跨句截取用 `…` 连接，并在 `notes` 说明跨句；
- 原文为非中文时保留原文语言，不改写。

### 5.3 支撑关系受控词表（3 值）

| 值 | 判据 | 建议权重 |
|---|---|---|
| `direct_support` | 证据原文直接陈述断言全部内容 | 高 |
| `partial_support` | 证据支撑断言，但缺限定/数值/对照 | 中，必须配 `uncertainty_items` |
| `indirect_inference` | 需一步以上逻辑推导才成立（含"作者推断"类断言） | 低，必须写推理链 |

### 5.4 证据类型受控词表（3 值）

| 值 | 用法 |
|---|---|
| `text_evidence` | 正文文字 |
| `figure_evidence` | 正文对图的文字陈述（如"Fig.2 显示…"），`figure_table_id` 必填 |
| `table_evidence` | 正文对表的文字陈述或表内文字单元格，`figure_table_id` 必填 |

禁止把"我看到的图里曲线走向"当证据——本 Skill 不读图内数值。

### 5.5 位置标注规范（全部 1-based）

| 字段 | 规则 | 缺失时 |
|---|---|---|
| `page` | 论文原始页码（PDF 印刷页码优先，无则用 PDF 物理页序并在 `notes` 注明） | `null` + 记不确定性 |
| `paragraph_index` | 本段落在本 Skill 处理文本范围内的段序 | `null` |
| `sentence_index` | 该句在所属段落内的句序 | `null` |
| `char_span` | 可选，段内字符起止 `[start, end)` | `[]` |
| `figure_table_id` | 如 `"Fig. 2"`、`"Table 3"` | `null` |

同一断言多段证据 → 分列多条 `evidence`，ID 用 `A001-E1 / A001-E2`。

### 5.6 找不到证据时

- `evidence` 数组留空（确无证据，Schema 允许空数组）；
- `confidence_score ≤ 0.4`；
- 必写一条 `uncertainty_items`，`item_type = "no_evidence"`；
- **严禁**用断言自身当证据，**严禁**编造一句"看似原文"的句子。

---

## 6. 情境处理：未报告、无法判断、冲突

| 情形 | 输出处置 | item_type |
|---|---|---|
| 原文压根没报告此项（如没给 SD、没给 n） | 不断言数值；断言只写原文有的话，`notes` 写"未报告 X" | `unreported_data` |
| 材料模糊、指代不明、无法判断 | 保留断言但 `certainty = "uncertain"`，`scope` 写清歧义 | `ambiguous_text` |
| 原文不同位置互相矛盾 | 两条断言都保留，各自绑各自证据，`notes` 互相引用，记冲突 | `source_conflict` |
| 证据在图表里、正文只有"见 Fig. X" | 断言可出，证据标 `figure_evidence`，说明未读图内数据 | `cross_media_evidence` |
| 问题超出材料范围 | 不回答该部分；`answer.direct_answer` 写"输入材料未涉及"，记一条 | `out_of_scope` |
| 输入无文本层/乱码/不可读 | `task_status = "failed"`，不产出断言 | `input_unreadable` |
| 只能处理部分材料 | `task_status = "partial"`，写清已处理页码范围与未处理部分 | `partial_coverage` |
| 元数据缺失 | 字段 `null`，记一条 | `missing_metadata` |

规则：**凡是写了"未报告/无法判断"的地方，正文、`notes`、`uncertainty_items` 三处表述必须一致**，不得一处含糊一处肯定。

---

## 7. 字段字典（完整）

### 7.1 顶层

| 字段 | 类型 | 必填 | 取值 / 说明 |
|---|---|---|---|
| `case_id` | string | 是 | 透传 `/input/case.json` 的案例标识，不得改写 |
| `task_status` | string | 是 | `success` / `partial` / `failed` |
| `status_reason` | string | 是 | 正常填"处理完成，无异常"；异常必写原因与可人工接管点 |
| `answer` | object | 是 | 科研问答结果，见 7.2 |
| `source_metadata` | object | 是 | 来源元数据，见 7.3 |
| `assertions` | array | 是 | 断言列表，可为空数组但须说明原因，见 7.4 |
| `quality_check` | object | 是 | 自检结果，见 7.7 |
| `uncertainty_items` | array | 是 | 不确定性清单，见 7.8 |
| `processing_log` | array | 是 | 步骤日志，见 7.9 |
| `skill_version` | string | 是 | 固定 `"nanopublication@1.0.0"` |

### 7.2 `answer`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `question` | string | 是 | 原问题；无问题则填任务说明摘要 |
| `direct_answer` | string | 是 | 只用已有断言组织答案，不得新增原文外内容 |
| `answer_assertion_ids` | array | 是 | 支撑答案的断言 ID，必须真实存在 |
| `answer_caveats` | string | 否 | 成立条件、未报告项、间接证据提示 |

### 7.3 `source_metadata`

| 字段 | 类型 | 必填 | 取值 / 说明 |
|---|---|---|---|
| `document_title` | string | 是 | 论文标题原文 |
| `document_id` | string\|null | 是 | DOI / PMID / arXiv / ISBN，无则 `null` |
| `id_type` | string\|null | 否 | `doi` / `pmid` / `arxiv` / `isbn` / `other` |
| `document_type` | string | 是 | `journal_article` / `conference_paper` / `preprint` / `thesis` / `book_chapter` / `other` |
| `authors` | array | 是 | 作者列表，按原文顺序；未知填空数组 |
| `publish_year` | number\|null | 是 | 四位年份数字 |
| `publish_source` | string | 是 | 期刊/会议/出版社名，未知填 `""` |
| `version` | string | 是 | 如 `preprint_v1` / `published` / `revised_2024-05`，未知填 `""` |
| `source_page_range` | array | 是 | `[起, 止]`；单页 `[3]` |
| `source_section` | string | 是 | `abstract` / `introduction` / `methods` / `results` / `discussion` / `conclusion` / `other` |
| `source_paragraph_range` | array | 是 | `[起, 止]` 段序 |
| `metadata_notes` | string | 是 | 缺失、歧义、冲突说明；无则 `""` |

### 7.4 `assertions[]`

| 字段 | 类型 | 必填 | 取值 / 说明 |
|---|---|---|---|
| `assertion_id` | string | 是 | `A001` 起三位递增，全文件唯一、不复用 |
| `assertion_text` | string | 是 | 单一命题的忠实表述，不得概括 |
| `assertion_type` | string | 是 | 见 4.4 四值 |
| `certainty` | string | 是 | 见 4.5 三值 |
| `scope` | string | 是 | 全部限定条件；无显式限定时写"原文未给出额外限定" |
| `spo` | object | 否 | `{subject, predicate, object}`：主体—关系—客体，见 7.5 |
| `confidence_score` | number | 是 | `0.0–1.0`，按 7.6 映射，不得凭感觉 |
| `confidence_rationale` | string | 是 | 一句话说明打分依据（引用支撑关系与确定性） |
| `evidence` | array | 是 | 至少 1 条；确无证据则空数组 + 记 `no_evidence` |
| `notes` | string | 是 | 补充、缺失、跨句、指代还原说明；无则 `""` |

### 7.5 `spo`（主体—关系—客体）

| 字段 | 类型 | 说明 |
|---|---|---|
| `subject` | string | 断言主体，带限定（如"10 μmol/L 化合物 A 处理 24 h 的 HepG2 细胞"） |
| `predicate` | string | 受控动词短语，见 7.5.1 |
| `object` | string | 客体/取值；未报告的数值写"（原文未报告）"，不得填估算 |

#### 7.5.1 谓词受控短语（推荐映射，避免自由动词）

| 语义 | 受控谓词 |
|---|---|
| 测量/观测到数值 | `测量值为` / `观测到` |
| 上升/下降 | `升高至` / `降至` / `高于` / `低于` |
| 因果推断 | `作者推断导致` |
| 相关 | `与…相关`（禁止写成因果） |
| 方法使用 | `采用` |
| 统计显著 | `统计显著性为` |
| 无显著差异 | `未见显著差异` |
| 表达/含量 | `表达水平为` / `含量为` |
| 适用条件 | `在…条件下成立` |

> 关系方向错误是高频扣分点：**"A 导致 B"不等于"A 与 B 相关"**，原文写"associated with"就只能是 `与…相关`。

### 7.6 `confidence_score` 映射（确定性 × 支撑强度）

| certainty \ support | `direct_support` | `partial_support` | `indirect_inference` | 无证据 |
|---|---|---|---|---|
| `confirmed` | 0.90 | 0.70 | 0.60 | 0.30 |
| `conditional` | 0.80 | 0.60 | 0.50 | 0.25 |
| `uncertain` | 0.75 | 0.55 | 0.50 | 0.20 |

补充扣减（在表值上减 0.05–0.15，累计不低于下限 0.10）：证据跨句且指代需还原、图表证据未读原始数据、原文存在相关矛盾表述、元数据关键字段缺失。

### 7.7 `quality_check`

| 字段 | 类型 | 说明 |
|---|---|---|
| `overall_quality` | string | `excellent`（无 issue 且全部 direct） / `good`（无 high issue） / `fair`（有 1–2 个 medium） / `poor`（存在 high） |
| `issue_count` | number | `issues` 长度，须一致 |
| `issues` | array | 每条含 `issue_id`（`Q001` 起）、`issue_type`、`target_assertion_id`、`issue_description`、`correction_suggestion`、`detected_by`（判据编号，如"4.1-否定单值测试"） |
| `pass` | boolean | 无 high issue 且格式合法时为 `true` |

`issue_type` 受控值：`granularity_too_coarse`、`granularity_too_fine`、`faithfulness_violation`、`evidence_mismatch`、`evidence_insufficient`、`relation_type_wrong`、`direction_reversed`、`subject_confusion`、`location_missing`、`metadata_missing`、`format_invalid`、`duplicate_assertion`。

### 7.8 `uncertainty_items[]`

| 字段 | 类型 | 说明 |
|---|---|---|
| `item_id` | string | `U001` 起 |
| `item_type` | string | 见第 6 节 item_type 列 |
| `related_assertion_id` | string\|null | 关联断言；全局性问题填 `null` |
| `description` | string | 具体缺什么、冲突在哪、指代何处不明 |
| `impact_level` | string | `high` / `medium` / `low` |
| `suggestion` | string | 复核动作（补查哪一节、索取哪项信息、保留哪个标注） |

### 7.9 `processing_log[]`

| 字段 | 类型 | 说明 |
|---|---|---|
| `step` | string | `1_input_parse` … `7_output`，固定七项 |
| `timestamp` | string | ISO 8601，可空串（平台会记录真实 trace） |
| `status` | string | `completed` / `partial` / `failed` |
| `detail` | string | 本步实际产出量（拆出几条、绑上几条、修了几处） |

### 7.10 ID 与去重规则

- 断言 ID 三位递增，删除后不复用；证据 ID 为 `断言ID-E序号`。
- **合并判据**：`subject` 相同 + `predicate` 相同 + `object` 相同（去除空白与标点差异）+ `scope` 实质相同 → 视为重复，合并为一条，多条证据按位置先后合并到同一 `evidence` 数组。
- **保留拆分判据**：数值不同、条件不同、主体不同、关系类型不同 → 一律不合并。
- 合并/拆分必须写入对应 `notes`，便于复核。

---

## 8. 输出 Schema（可直接做校验用）

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "nanopublication_result",
  "type": "object",
  "required": ["case_id", "task_status", "status_reason", "answer", "source_metadata", "assertions", "quality_check", "uncertainty_items", "processing_log", "skill_version"],
  "properties": {
    "case_id": { "type": "string" },
    "task_status": { "enum": ["success", "partial", "failed"] },
    "status_reason": { "type": "string" },
    "skill_version": { "type": "string" },
    "answer": {
      "type": "object",
      "required": ["question", "direct_answer", "answer_assertion_ids"],
      "properties": {
        "question": { "type": "string" },
        "direct_answer": { "type": "string" },
        "answer_assertion_ids": { "type": "array", "items": { "type": "string" } },
        "answer_caveats": { "type": "string" }
      }
    },
    "source_metadata": {
      "type": "object",
      "required": ["document_title", "document_id", "document_type", "authors", "publish_year", "publish_source", "version", "source_page_range", "source_section", "source_paragraph_range", "metadata_notes"],
      "properties": {
        "document_title": { "type": "string" },
        "document_id": { "type": ["string", "null"] },
        "id_type": { "type": ["string", "null"] },
        "document_type": { "enum": ["journal_article", "conference_paper", "preprint", "thesis", "book_chapter", "other"] },
        "authors": { "type": "array", "items": { "type": "string" } },
        "publish_year": { "type": ["number", "null"] },
        "publish_source": { "type": "string" },
        "version": { "type": "string" },
        "source_page_range": { "type": "array", "items": { "type": "number" } },
        "source_section": { "enum": ["abstract", "introduction", "methods", "results", "discussion", "conclusion", "other"] },
        "source_paragraph_range": { "type": "array", "items": { "type": "number" } },
        "metadata_notes": { "type": "string" }
      }
    },
    "assertions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["assertion_id", "assertion_text", "assertion_type", "certainty", "scope", "confidence_score", "confidence_rationale", "evidence", "notes"],
        "properties": {
          "assertion_id": { "type": "string", "pattern": "^A[0-9]{3}$" },
          "assertion_text": { "type": "string", "minLength": 4 },
          "assertion_type": { "enum": ["fact_statement", "experiment_result", "conclusion_inference", "method_description"] },
          "certainty": { "enum": ["confirmed", "conditional", "uncertain"] },
          "scope": { "type": "string" },
          "spo": {
            "type": "object",
            "properties": {
              "subject": { "type": "string" },
              "predicate": { "type": "string" },
              "object": { "type": "string" }
            }
          },
          "confidence_score": { "type": "number", "minimum": 0, "maximum": 1 },
          "confidence_rationale": { "type": "string" },
          "evidence": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["evidence_id", "evidence_text", "evidence_type", "support_relation", "location"],
              "properties": {
                "evidence_id": { "type": "string", "pattern": "^A[0-9]{3}-E[0-9]+$" },
                "evidence_text": { "type": "string", "minLength": 2 },
                "evidence_type": { "enum": ["text_evidence", "figure_evidence", "table_evidence"] },
                "support_relation": { "enum": ["direct_support", "partial_support", "indirect_inference"] },
                "location": {
                  "type": "object",
                  "required": ["page", "paragraph_index", "sentence_index"],
                  "properties": {
                    "page": { "type": ["number", "null"] },
                    "paragraph_index": { "type": ["number", "null"], "minimum": 1 },
                    "sentence_index": { "type": ["number", "null"], "minimum": 1 },
                    "char_span": { "type": "array", "items": { "type": "number" } },
                    "figure_table_id": { "type": ["string", "null"] }
                  }
                }
              }
            }
          },
          "notes": { "type": "string" }
        }
      }
    },
    "quality_check": {
      "type": "object",
      "required": ["overall_quality", "issue_count", "issues", "pass"],
      "properties": {
        "overall_quality": { "enum": ["excellent", "good", "fair", "poor"] },
        "issue_count": { "type": "number" },
        "issues": { "type": "array", "items": { "type": "object" } },
        "pass": { "type": "boolean" }
      }
    },
    "uncertainty_items": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["item_id", "item_type", "related_assertion_id", "description", "impact_level", "suggestion"],
        "properties": {
          "item_id": { "type": "string", "pattern": "^U[0-9]{3}$" },
          "item_type": { "type": "string" },
          "related_assertion_id": { "type": ["string", "null"] },
          "description": { "type": "string" },
          "impact_level": { "enum": ["high", "medium", "low"] },
          "suggestion": { "type": "string" }
        }
      }
    },
    "processing_log": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["step", "status", "detail"],
        "properties": {
          "step": { "type": "string" },
          "timestamp": { "type": "string" },
          "status": { "enum": ["completed", "partial", "failed"] },
          "detail": { "type": "string" }
        }
      }
    }
  }
}
```

---

## 9. 输出前自检清单（逐项打勾，任一不通过不得标记 `pass: true`）

1. **粒度**：每条断言都能通过 4.1 的否定单值测试与连接词测试；没有一条包含"并且/同时/因此"串联的多命题。
2. **忠实**：`assertion_text` 与原文逐字对照，无新增、无删限定、无同义替换、无升华。
3. **证据相关性**：逐字比对 `evidence_text` 与原文；`evidence_text` 中不含断言未提及的无关结论。
4. **证据充分性**：断言中的每个限定（浓度/时长/n/p/范围/in vitro）在证据中都有对应文字；缺则降为 `partial_support`。
5. **方向与主体**：`spo.subject`/`object` 未互换；相关关系未被写成因果；转述他文的断言在 `scope` 已标"转述他文，非本文实验"。
6. **定位**：每条证据 `page/paragraph_index/sentence_index` 至少各有一项非 `null`；全 `null` 必须挂 `location_missing` issue。
7. **来源**：`document_title`、`document_type`、`publish_year`、`source_section`、`source_page_range` 已尽力填充；缺失项在 `metadata_notes` 与 `uncertainty_items` 有记录。
8. **一致性**：`status_reason` ↔ `uncertainty_items` ↔ 各 `notes` 对同一事实的表述不矛盾；`issue_count` 与 `issues` 长度一致；`answer_assertion_ids` 全部真实存在。
9. **格式**：纯 JSON、无注释、无尾逗号、无 Markdown 包裹；枚举值全部在受控表内；数字未写成字符串。
10. **状态诚实**：`failed`/`partial` 时未虚构已完成内容；`processing_log` 七项齐全且与实际动作对应。

可选自动校验：本 Skill 附带 `scripts/validate_result.py`（仅用标准库 `json`，做关键字段手工检查，非完整 jsonschema 校验）。执行

```bash
python3 scripts/validate_result.py /app/output/result.json
```

校验失败返回非零退出码，并逐条打印违规项（JSON 路径 + 原因）。无 Python 时以第 9 节人检为准。

---

## 10. 失败处理与人工接管

| 失败现象 | 立即动作 | 人工接管点 |
|---|---|---|
| PDF 无文本层 / 乱码 | 先尝试平台 `ocr-tool`；仍不可读则 `task_status=failed`，`item_type=input_unreadable` | 需人工提供可复制版 PDF 或高质量 OCR |
| `/input/case.json` 缺字段 | 用 `task.md`（先 `/input/task.md` 后工作目录）兜底；仍缺则记 `missing_metadata`，`partial` | 补齐 case 字段后重跑 |
| 输出被截断（token 上限） | 先落盘 `result.json` 的已有断言（保证 JSON 合法闭合），`task_status=partial`，`detail` 写明"已处理至 A0xx/共 N 条" | 分批续跑剩余段落 |
| 断言找不到任何证据 | 保留断言、`evidence: []`、`confidence_score ≤ 0.4`、记 `no_evidence` | 人工回原文核实是否本 Skill 漏读 |
| 两次运行结果不一致 | 检查是否温度/模型不同；保留两份 `result.json` 并比对各 `evidence_id`，差异写 `uncertainty_items` | 以逐字比对原文者为准 |
| 断言与证据冲突（如证据说升高、断言写降低） | 立即改断言，或标 `issues: evidence_mismatch` 并降分 | 人工确认原文实际表述 |
| 图表证据无法确认 | 标 `figure_evidence` + `cross_media_evidence`，不写图内数值 | 人工看原图核对 |

---

## 11. 已知限制（写进说明，不隐瞒）

1. 只处理有文本层的材料；无文本层时依赖平台 `ocr-tool`，本 Skill 自身不实现 OCR，OCR 仍失败即置 `failed`。
2. 不读图表内数值，只取正文对图表的文字陈述。
3. 不做事实真伪、学术争议、领域共识判断。
4. 不做跨文献合并与外部检索溯源（仅记录本文来源链）。
5. 段落级优化；超长全文需分批，单次覆盖率须在 `status_reason` 写明。
6. 位置定位精度为"页 + 段 + 句"；`char_span` 为可选增强，非强制。

---

## 12. 版本与维护

- 版本：`nanopublication@1.0.0`
- 依赖：无第三方库；可选 `python3` 做 Schema 自检
- 变更记录：v1.0.0 建立 4 项原子性判据、证据删减测试、`confidence_score` 映射表、去重合并规则、10 项自检清单
- 维护建议：新增受控词表值时同步更新第 7 节字段字典与第 8 节 Schema，并在本段记录版本号与日期
- 复用建议：字段字典可直接作为他人项目的标注规范；第 4/5 节判据可作为人工标注培训材料
- 实测记录（开发期自测，非正式案例、非平台评分）：
  - 测试 1：取真实论文 Alimohammadi 等 2020（ChemistrySelect，DOI 10.1002/slct.201903179）摘要 6 句，按第 4 节规则逐句拆解，得 9 条断言（方法 3、结果 3、推断 3），证实规则能把"一句多命题/多数值"拆开，未出现整段合并。
  - 测试 2：第 2.5 节 HepG2 示例 3 句拆 5 条，含 `partial_support`（凋亡率缺数值）与 `indirect_inference`（"潜在活性"归为作者推断），验证第 7.6 节置信度映射表与第 5.3 节支撑关系词表可用。
  - 发现：分子对接句 "may act … through inhibition of Abl kinase and T315I Abl mutant" 的并列机制易被合并，已按第 4.2 节"并列逐条拆"处理（见 `references/assertion-examples.md` A008/A009）。
  - 约束：以上仅验证规则自身，不涉及平台 3 个固定案例与白板；正式增益以平台对照结果为准，本文件不自述分数。

---

## 13. 相对基础 Agent 的新增能力与增益验证

### 13.1 新增能力（对照"不加 Skill 的基础 Agent"）

基础 Agent 面对"把论文段落拆成断言并给依据"时，常见失败是：整段塞进一个字段、不做证据定位、关系方向写错、缺失条件限定、把图表文字当图内数据。本 Skill 新增以下可稳定执行的能力：

1. **原子性强制**：四项判据（4.1）把"可判断真假的单一命题"从语感变成可操作测验，阻止整段/整句合并。
2. **最小充分证据**：删减测试 + 缺口测试（5.1）使证据片段最小化且逐限定对齐，阻止"证据过长/过短"。
3. **关系方向约束**：谓词受控短语（7.5.1）区分"相关/因果/导致/无差异"，阻止方向颠倒。
4. **确定性 × 支撑强度的置信度**：映射表（7.6）把分数从凭感觉变为可复现。
5. **全链路溯源**：断言→证据→页/段/句→论文/作者/年份/版本的字段链（第 7 节）与去重规则（7.10）。
6. **诚实降级**：未报告/无法判断/冲突/无文本层的分类处置（第 6、10 节），不把"无法判断"写成事实。

### 13.2 增益验证方法（公平对照，不自我打分数）

平台已做"基础 Agent vs Skill Agent"白板对照；本 Skill 另提供可复现的自测方案，供第三方独立复核：

1. 取同篇论文同段、同一模型与工具权限，跑两遍：一遍无 Skill、一遍加载本 Skill。
2. 记录四个指标：① 断言条数（粒度，应≥句子数，且无整段合并）；② 断言-证据逐字一致率；③ 位置标注覆盖率（page/paragraph/sentence 非空比例）；④ `spo` 关系方向错误率。
3. 用 `scripts/validate_result.py` 对两份 `result.json` 做结构自检，比较违规条数。
4. 以"违规条数下降 + 位置覆盖率上升"作为增益的客观证据；不引用未经核实的基准分数。

### 13.3 可复用资产

- `references/assertion-examples.md`：20 条断言样例（含规则覆盖速查）。
- `references/exercise-set.md`：3 组练习段落（含拆解提示），供标注培训与能力测试。
- `scripts/validate_result.py`：结构自检脚本。
- 第 7 节字段字典 + 第 8 节 Schema：可直接作为他人项目的标注规范与校验契约。
