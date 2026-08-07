# Batch 113 — Leader Verdict（知识中心关联基座 + UI 交互用例）

> **Leader (🎯)** | Date: 2026-08-07 | Decision: **APPROVED**

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 需求聚焦 | PASS | 完整批次；范围=关联基座入库（C112-1）+ 交互用例（C112-2），符合用户 2026-08-07 方向，无蔓延 |
| 实现质量 | PASS | 关联基座脚本交叉校验 0 issues；capture code=0 + RAG 命中；19 条交互用例落库 |
| 证据 | PASS | 校验 JSON + capture/search 证据 + 路径/用例汇总 + 目标页 5/5 实测 |
| 诚实性 | PASS | 关联数据全部来自地图/生产实测，无编造；粒度粗/重复边如实登记 P3 |

## 关键决策（已批准）

1. **关联基座 = 用例生成前置**：知识中心 source#17 承载「模块-接口-功能」关联，
   后续用例生成/AI 生成提示注入该基座，先定位关联再产出用例（用户方向落地）。
2. **交互用例以生产实测驱动**：交互路径从 40 页勘察 links 提取，用例按场景法（正负向/步骤/预期/P0）
   落库交互测试域；不靠需求杜撰。
3. **P3 遗留**：source 章节化粒度、交互边拓扑化 → 登记 B113-1/B113-2，不阻塞。

## 抽检通过

- ✅ `build-association-baseline.py` — 解析 4 张地图表格 + 31 接口/xhr-samples、konfi formKey/inventory、
  运营菜单/nav 全量交叉校验 0 issues
- ✅ `sync-association-knowledge.py` — capture code=0 id=17；sources total=17；5 组查询各 5 命中
- ✅ `generate-interaction-cases.py` — 19 条用例（16 正/3 负/18 P0）落库 id 1814-1832；幂等 existing=0
- ✅ 生产实测：match-replay/q/news/search/worldcup-2026/my 5 页 HTTP 200
- ✅ scan-common-bugs HARD=0；py_compile 0 错误

## 判决

**APPROVED**：进入一次总确认 → push → Draft PR → required checks → 合入 main。

## 下一批次 Leader 条件

- C113-1（P3）：交互路径拓扑图化（3172 边收敛为模块级拓扑）+ 关键交互路径挂 UI 自动化回归。
- C113-2（P3）：知识中心 source#17 章节化拆细，提升 RAG 检索粒度。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 用户方向=知识中心关联优先 | 关联基座入库 source#17 + 用例生成前置 | `docs/体育平台-关联基座.json` + C112-1 |
| 用例缺交互维度 | 生产 links 提取路径 + 场景法交互用例 | `generate-interaction-cases.py` + C112-2 |
| MD 表格解析脆弱 | dry-run 断言（表头/多接口/相对路径）修复 | `build-association-baseline.py` |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1d / 实际 0.5d | 0/0/0/2 | 1 | 工具链 | MD 表格解析先 dry-run 断言再落库 |

**技能使用**：`cameltv-agent-team`、`test-case-design`、`cameltv-bug-guard`。
