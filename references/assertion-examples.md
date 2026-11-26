# 20 条断言样例（示意，可直接复用为标注规范）

本文件给出 20 条断言样例，覆盖第 4 节的四类断言、三类确定性、第 5 节的三类支撑关系与三类证据类型，以及并列/因果/多数值/指代还原/未报告/图表证据/冲突等边界情形。全部为**示意样例**，用于说明字段用法与判据，不是任何正式测试案例的预制答案。

正文来源一（真实）：Alimohammadi, Mostafavi, Mahdavi, "Thiourea Derivatives Based on the Dapsone-Naphthoquinone Hybrid…", ChemistrySelect, 2020, DOI 10.1002/slct.201903179（摘要，第 1 段）。此处仅取其摘要文字作拆解演示，页码/段落/句序按摘要按序计。

正文来源二（示意）：本 SKILL.md 第 2.5 节 HepG2 示例段（已声明为示例，非正式案例）。

---

## 来源一：Thiourea 摘要（6 句 → 9 条断言）

原文（6 句）：
1. According to the structure-activity relationships (SAR), we synthesized a series of novel thiourea derivatives based on the dapsone-naphthoquinone hybrid by the nucleophilic addition reaction of various primary/secondary amines to 2-[4-(4-isothiocyanato-benzenesulfonyl)-phenylamino]-[1,4]naphthoquinone (4).
2. All thiourea derivatives (5 a-j) were screened for in vitro anticancer activity against human leukemia cell line (K562).
3. Thiourea derivative containing N-methyl piperazine (5 h) was identified as the most effective molecule with IC50= 5.8±0.55 μM.
4. Antimicrobial activity of thiourea derivatives (5 a–j) was evaluated in vitro against six strains of bacteria (Staphylococcus aureus, Staphylococcus epidermidis, Bacillus subtilis, Escherichia coli, Salmonella enterica and Klebsiella pneumoniae) and a fungus Candida kefyr by the microdilution method.
5. Interestingly, compound 5 h exhibited better antibacterial activity compared with the dapsone as a positive control against S. epidermidis.
6. The molecular docking studies indicated that compound 5 h may act as anticancer agent through the inhibition of Abl kinase and T315I Abl mutant.

| ID | 断言（assertion_text） | type | certainty | 支撑 | 证据片段（最小） | 规则要点 |
|---|---|---|---|---|---|---|
| A001 | 作者通过伯/仲胺与化合物 4 的亲核加成反应合成了基于 dapsone-naphthoquinone 杂合体的一系列硫脲衍生物。 | method_description | confirmed | direct_support | "we synthesized a series of novel thiourea derivatives based on the dapsone-naphthoquinone hybrid by the nucleophilic addition reaction…to …(4)"（句 1） | 方法描述；长限定全保留进 scope |
| A002 | 硫脲衍生物 5a–j 对 K562 人白血病细胞系进行了体外抗癌活性筛选。 | method_description | confirmed | direct_support | "All thiourea derivatives (5 a-j) were screened for in vitro anticancer activity against human leukemia cell line (K562)."（句 2） | 方法描述；对象+方法+细胞系 |
| A003 | 含 N-甲基哌嗪的衍生物 5h 被认定为 5a–j 中最有效的分子。 | experiment_result | confirmed | direct_support | "Thiourea derivative containing N-methyl piperazine (5 h) was identified as the most effective molecule"（句 3） | "最有效"（相对比较）与数值拆开 |
| A004 | 化合物 5h 对 K562 的 IC50 为 5.8±0.55 μM。 | experiment_result | confirmed | direct_support | "with IC50= 5.8±0.55 μM"（句 3） | 数值单独成条；"对象+数值+条件" |
| A005 | 硫脲衍生物 5a–j 以微量稀释法对六种细菌与真菌 Candida kefyr 进行了体外抗菌活性评价。 | method_description | confirmed | direct_support | "Antimicrobial activity of thiourea derivatives (5 a–j) was evaluated in vitro against six strains of bacteria (…) and a fungus Candida kefyr by the microdilution method."（句 4） | 列举的菌株是范围的一部分，不逐菌拆成七条 |
| A006 | 化合物 5h 对 S. epidermidis 的抗菌活性优于阳性对照 dapsone。 | experiment_result | confirmed | direct_support | "compound 5 h exhibited better antibacterial activity compared with the dapsone as a positive control against S. epidermidis."（句 5） | 比较对象（dapsone）与对象（S. epidermidis）都进 scope |
| A007 | 分子对接研究提示 5h 可能作为抗癌剂。 | conclusion_inference | uncertain | indirect_inference | "The molecular docking studies indicated that compound 5 h may act as anticancer agent"（句 6） | "may act"→uncertain；主体是"研究提示"，非实验证实 |
| A008 | 分子对接提示 5h 通过抑制 Abl 激酶发挥（可能的抗癌）作用。 | conclusion_inference | uncertain | indirect_inference | "through the inhibition of Abl kinase"（句 6） | 并列机制 "Abl kinase and T315I Abl mutant" 拆为两条 |
| A009 | 分子对接提示 5h 通过抑制 T315I Abl 突变体发挥（可能的抗癌）作用。 | conclusion_inference | uncertain | indirect_inference | "and T315I Abl mutant"（句 6） | 同上，并列拆分 |

---

## 来源二：HepG2 示例段（示意，第 2.5 节，3 句 → 5 条断言）

| ID | 断言 | type | certainty | 支撑 | 证据片段 | 规则要点 |
|---|---|---|---|---|---|---|
| A010 | 本实验在 25℃、1 atm 条件下采用 MTT 法检测细胞活力。 | method_description | confirmed | direct_support | "在 25℃、1 atm 条件下，采用 MTT 法检测细胞活力。" | 条件（25℃、1 atm）进 scope |
| A011 | 10 μmol/L 化合物 A 处理 HepG2 细胞 24 h 后，细胞存活率降至 42.3%。 | experiment_result | confirmed | direct_support | "浓度为 10 μmol/L 的化合物 A 处理 24 h 后，HepG2 细胞存活率降至 42.3%" | 浓度/时长/细胞系三限定齐全 |
| A012 | 上述存活率下降达到统计显著（p < 0.05）。 | experiment_result | confirmed | direct_support | "（p < 0.05）" | 统计显著性与数值拆为两条 |
| A013 | 10 μmol/L 化合物 A 处理 24 h 后 HepG2 细胞凋亡率较对照升高。 | experiment_result | confirmed | partial_support | "且细胞凋亡率显著升高" | 缺具体数值与对照定义→partial_support + uncertainty |
| A014 | 作者认为化合物 A 具有抑制肝癌细胞增殖的潜在活性。 | conclusion_inference | uncertain | indirect_inference | "该结果表明化合物 A 具有抑制肝癌细胞增殖的潜在活性。" | "该结果表明/潜在"→作者推断、uncertain |

---

## 边界情形样例（6 条，演示异常/特殊处置）

| ID | 断言 | type | certainty | 支撑 | 证据片段/位置 | 规则要点 |
|---|---|---|---|---|---|---|
| A015 | 该文转述：结构-活性关系（SAR）是合成设计的依据。 | fact_statement | confirmed | direct_support | "According to the structure-activity relationships (SAR), we synthesized…"（句 1） | 转述背景/他人知识，scope 标"转述他文，非本文实验" |
| A016 | Fig. 2 显示 5h 与 Abl 激酶口袋存在氢键相互作用（正文文字陈述）。 | experiment_result | confirmed | direct_support | 正文 "Fig.2 shows…"（figure_evidence，figure_table_id="Fig. 2"） | 图表证据：只取正文文字陈述，不读图内数值 |
| A017 | 5h 对六种细菌的最小抑菌浓度（MIC）数值 | —（不产出断言） | — | no_evidence | 摘要未报告各菌 MIC 数值 | 未报告数据：不断言数值，记 unreported_data |
| A018 | 5h 的抗菌活性是否强于所有 5a–j 同系物 | experiment_result | uncertain | partial_support | 原文仅比较 5h 与 dapsone，未与其余 5a–j 逐一比较 | 原文未报告同系物间比较→不写"最强" |
| A019 | 摘要与正文对 5h IC50 表述不一致（示例） | —（保留两条冲突断言，各自绑证据） | — | — | 摘要 vs 正文各一句 | source_conflict：两条都保留，notes 互相引用 |
| A020 | "该化合物"指代 5h（指代还原示例） | experiment_result | confirmed | direct_support | 跨句 "上述处理"→最小先行词 "含 N-甲基哌嗪的 5h" 一并纳入 | 指代还原：证据须带最小先行词，notes 说明跨句 |

---

## 规则覆盖速查

- 断言类型四值：fact_statement(A015)、experiment_result(A003/A004/A006/A011…)、conclusion_inference(A007/A014…)、method_description(A001/A002/A005/A010)。
- 确定性三值：confirmed（多数）、uncertain（A007/A008/A009/A014/A018）、conditional（见 SKILL.md 第 4.5 节判据，本集未强造条件句）。
- 支撑关系三值：direct_support（多数）、partial_support（A013/A018）、indirect_inference（A007/A008/A009/A014）。
- 证据类型三值：text_evidence（多数）、figure_evidence（A016）、table_evidence（未单独造，规则同 figure_evidence）。
- 拆分动作：并列（A008/A009）、多数值（A003/A004、A011/A012）、因果/推断（A014、A007）。
- 异常处置：unreported_data（A017）、source_conflict（A019）、指代还原（A020）、partial_support（A013/A018）。

> 以上样例用于说明方法，正式案例须以平台实际材料为准逐字复核，不得照抄本文件。
