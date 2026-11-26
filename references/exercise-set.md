# 可复用题集（练习用，非正式案例、非预制答案）

本文件是 3 组练习段落，供标注人员/Agent 练习第 4、5 节规则。每题只给"拆解提示"（预期拆法要点），不写逐条标准答案——目的是训练，不是提供正式测试答案。两组来自真实论文摘要（可逐字溯源），一组为合成的边界情形题。

---

## 练习 1：真实论文摘要（化学/生物医学，6 句）

> Alimohammadi, Mostafavi, Mahdavi, ChemistrySelect, 2020, DOI 10.1002/slct.201903179（摘要）：
>
> According to the structure-activity relationships (SAR), we synthesized a series of novel thiourea derivatives based on the dapsone-naphthoquinone hybrid by the nucleophilic addition reaction of various primary/secondary amines to 2-[4-(4-isothiocyanato-benzenesulfonyl)-phenylamino]-[1,4]naphthoquinone (4). All thiourea derivatives (5 a-j) were screened for in vitro anticancer activity against human leukemia cell line (K562). Thiourea derivative containing N-methyl piperazine (5 h) was identified as the most effective molecule with IC50= 5.8±0.55 μM. Antimicrobial activity of thiourea derivatives (5 a–j) was evaluated in vitro against six strains of bacteria (Staphylococcus aureus, Staphylococcus epidermidis, Bacillus subtilis, Escherichia coli, Salmonella enterica and Klebsiella pneumoniae) and a fungus Candida kefyr by the microdilution method. Interestingly, compound 5 h exhibited better antibacterial activity compared with the dapsone as a positive control against S. epidermidis. The molecular docking studies indicated that compound 5 h may act as anticancer agent through the inhibition of Abl kinase and T315I Abl mutant.

**拆解提示**：
- 6 句应拆出约 9 条断言（方法 3、结果 3、推断 3），而不是 6 条或 1 条。
- 第 3 句的"最有效"与"IC50=5.8±0.55 μM"是两个命题，应拆开（多数值拆）。
- 第 6 句是并列机制 `Abl kinase and T315I Abl mutant`，按第 4.2 节"并列逐条拆"；且含 "may act"，`certainty=uncertain`、`assertion_type=conclusion_inference`。
- 易错点：把第 4 句的 7 种菌/真菌逐条拆成 7 条（应作为一次评价的列举范围，合 1 条）。

---

## 练习 2：真实论文摘要（有机化学，2 句）

> Liu, Hu, Xu, Lu, Yu, Lin, Chemistry of Natural Compounds, 2015, DOI 10.1007/s10600-015-1266-z（摘要）：
>
> A facile and efficient one-step synthesis of a novel phenanthroindolizine skeleton was developed via the Vilsmeier–Haack reaction of accessible 18-acetamino-7-oxo-dehydroabietane. The structure and stereochemistry were confirmed by NMR, HR-MS, elemental analysis, and X-ray crystal structure analysis (XSA), and the proposed reaction pathway for the Vilsmeier-Haack reaction includes an unusual conjugate addition of enol to chloromethyleneiminium salt and intramolecular cyclization reaction.

**拆解提示**：
- 第 1 句是方法描述（`method_description`），1 条。
- 第 2 句由"并且/以及"串联两个命题：结构确认（`experiment_result`，confirmed）与反应途径推断（`conclusion_inference`，uncertain）——按连接词切开。
- 结构确认的四种方法（NMR、HR-MS、元素分析、XSA）是并列证据手段，不必再拆成四条。

---

## 练习 3：合成的边界情形题（含图引用、未报告、转折）

> 某论文结果节（示意，非真实原文）：
>
> 与对照组相比，化合物 B 处理 48 h 后肿瘤体积缩小 36%（p < 0.01），但体重无明显变化。如图 3 所示，肿瘤生长曲线随时间下降。该组的中位生存期未在文中报告。

**拆解提示**：
- 第 1 句含转折"但"：肿瘤体积缩小（`experiment_result`，confirmed）与体重无变化（`experiment_result`，confirmed，注意"无显著差异"谓词）拆两条。
- 图 3 证据：只取正文文字陈述，标 `figure_evidence`、`figure_table_id="Fig. 3"`，不读曲线数据。
- "中位生存期未报告"：不断言数值，记 `unreported_data`，不写估算。

---

> 以上题集用于复用与训练；正式评测以平台固定 3 个案例的实际材料为准，逐字复核。
