# Nanopublication Skill

科研阅读与 Nanopublication 结构化 Skill：把科研论文段落拆解为单一可独立判断真假的细粒度断言，为每条断言绑定最小充分证据片段与页码/段落/句子级位置，补全论文-作者-年份-版本溯源元数据，输出可被下游程序直接解析的 JSON。

## 仓库结构

- `SKILL.md` — Skill 入口（含用途、适用条件、调用方式、输入输出、7 步流程、断言/证据判据、字段字典、JSON Schema、自检清单、异常处理、维护记录）
- `references/assertion-examples.md` — 20 条断言样例 + 规则覆盖速查
- `references/exercise-set.md` — 3 组练习段落（含拆解提示）
- `scripts/validate_result.py` — `result.json` 结构自检脚本（仅标准库 `json`）

## 一句话说明

输入一段真实科研论文文本 + 任务问题，输出一份"每条断言都能回到原文某句、每个来源字段都能追溯到论文"的结构化 JSON：拆得细、对得上、追得回、读得懂。

## 本仓库对应的赛题

北京化工大学高校分站赛 · 第一期「AI 文献阅读与学术写作」· 阅读 14｜Nanopublication（challenge-id: `product-arena-09-0e8befd4`）。
