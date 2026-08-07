# Batch 114 — PRD（交互路径拓扑图 + UI 自动化回归 + 知识中心章节化）

> **Product (🟦)** | Date: 2026-08-07 | Status: Review

```markdown
mode: full
豁免理由: 无（含 UI 自动化 spec 扩展 + 知识中心章节化入库 + 拓扑数据，走完整六部门流水线）。
非目标:
- 平台 UI job 定时能力扩展（B112-3，候选 C112-3，本批仍以手动/CI 触发）
- Test5 899 端点契约（C111-4 继续 Deferred）
- news/get 服务端缺陷（B112-1）
- 运营后台生产账号深度操作（只读口径维持）
```

## 1. 问题陈述

Batch 113 已沉淀知识中心关联基座（source#17）并补充 19 条交互用例（C112-1/C112-2 关闭），
但用户方向仍有 3 个明确缺口（Batch 113 Leader 条件 C113-1/C113-2 + 交互落地）：

1. **交互路径未拓扑化**：3172 条「页面→入口→目标页」边是扁平清单，未收敛为模块级拓扑图，
   无法直接支撑用例完整性核对与自动化回归挂接（C113-1）。
2. **交互用例未自动化**：19 条交互用例只落库，未挂 Playwright 回归——页面点击/跳转/返回
   没有自动化验证，回归靠人工（C113-1 关键交互路径挂 UI 自动化）。
3. **知识中心检索粒度粗**：source#17 为整篇关联基座，RAG 检索按模块命中精度不足（C113-2）。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| 交互拓扑 | 3172 边扁平清单 | 模块级拓扑图（nodes/edges + 入口聚合），落盘 + 文档 |
| 交互 UI 自动化 | 0 条交互自动化 | 关键交互路径 Playwright spec ≥8 条（跳转/返回/目标渲染），本地 10/10 + 平台 job 运行 |
| 知识中心章节化 | source#17 整篇 | 关联基座按模块章节化入库，模块名检索命中对应章节 |
| C 条件 | C113-1/C113-2 Open | 关闭 + 证据 |

## 3. 用户故事 + 验收标准

- As a **QA**, I want 交互路径有模块级拓扑图，so that 用例完整性可核对、遗漏可发现。
  - Given 3172 边，When 收敛为模块拓扑（首页→赛事详情→直播间 等），Then 拓扑 JSON/图落盘，覆盖 P0 模块闭环。
- As a **QA**, I want 关键交互路径自动化回归，so that 页面点击/跳转/返回持续受控。
  - Given 关键交互路径 spec，When 本地与平台 job 执行，Then 全部通过并产出报告证据。
- As a **用例生成者**, I want 知识中心按模块检索关联，so that RAG 命中更精准。
  - Given 章节化入库，When 检索「首页」「直播间」等模块词，Then 命中对应章节 source。

## 4. 技术考量

- **拓扑生成**：`build-interaction-topology.py` 消费 `evidence/batch-113/interaction-paths.json`，
  按 from_module/to_module 聚合边 + 入口合并 → `interaction-topology.json`（nodes/edges/p0 标记）+ 文档图。
- **UI 自动化**：新增 `backend/tests/playwright/specs/production-interaction.spec.ts`
  （复用只读守卫 production-p0-contract）：首页→赛事详情→直播间、首页→回放、资讯列表→详情、
  搜索→结果、我的渲染、浏览器返回恢复等 ≥8 条；本地执行 + 平台 UI job（新增或复用 job）触发核对。
- **知识中心章节化**：`sync-association-knowledge.py` 增强（或新增章节化脚本）：按用户模块/运营模块
  逐章节 capture（每章节独立 title/内容），检索模块词验证命中对应 source。
- **风险**：平台 job 执行依赖守卫（B112-4 已修复）与站点可达；章节化 capture 依赖 KNOWLEDGE_INGEST_ENABLED。

## 5. 范围

**纳入**：交互拓扑生成与文档；交互 UI 自动化 spec + 本地/平台执行证据；知识中心章节化入库 + 检索验证；
C113-1/C113-2 关闭。

**非目标**（见头部）。

## 6. 上线计划

| 阶段 | 内容 | 出口标准 |
|------|------|---------|
| S1 | 批次工件 + 看板 + 交互拓扑生成 | 拓扑 JSON + 文档落盘 |
| S2 | 交互 UI 自动化 spec + 本地执行 | spec ≥8 条本地全过 |
| S3 | 平台 UI job 触发核对 + 知识中心章节化 | 平台运行通过 + 章节化检索命中 |
| S4 | QA 硬门禁 + QA/Leader + 一次总确认 | 工件齐全 + 审计 0 硬错 |

## 7. 技能使用

- `cameltv-agent-team` → 六部门流水线
- `playwright-cli` / `playwright-skill` → 交互自动化验证
- `test-case-design` → 交互用例核对
- `cameltv-bug-guard` → 入库/脚本避坑
