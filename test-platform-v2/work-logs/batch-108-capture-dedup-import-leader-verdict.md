# Batch 108 — Leader Verdict（capture 去重误判修复 + 规范导入闭环）

> **Leader (🎯)** | Date: 2026-08-06 | Decision: **APPROVED（待一次总确认）**

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 需求聚焦 | PASS | 完整批次；范围=根因修复 + 错误语义 + 配置 + 导入闭环，无蔓延 |
| 实现质量 | PASS | CaptureIngestResult 类型化；路由 503/409/500/200 映射；hooks 容错；生产开关对齐 |
| 证据 | PASS | 生产库 hash 核查 + 本地复现 + 107 pytest + API sources 实测 id=6 可见 |
| 诚实性 | PASS | 部署环境开关未开如实登记 C108-1；vector_search 子项保持 Open |
| 门禁 | PASS | pytest 107 / ruff / alembic 单头 / scan HARD 0 / boundary PASS |
| 风险 | 低 | API capture 生产可用依赖 Railway 环境变量（人工步骤），已登记 |

## 关键决策（已批准）

1. capture 入库结果从 `int | None` 升级为 `CaptureIngestResult(reason, source_id)`，四种语义互不混义。
2. 路由按 reason 映射：disabled→503 明确提示 / duplicate→409 / error→500+日志 / created→200+id。
3. `_post_ingest_hooks` 失败仅记日志，不翻转已提交的入库成功。
4. `KNOWLEDGE_INGEST_ENABLED=true` 写入 production.env(.example)，与 docker-compose 默认一致。
5. **C107-1 关闭**：规范文档已入库生产知识中心（source id=6，sources API 可见）；C102-2 capture 子项关闭。

## 抽检通过

- ✅ 本地复现：同内容去重 / 异内容新建 / 开关关 None，确认原 409 非去重逻辑问题
- ✅ 单测 107/107；路由 4 类响应断言通过
- ✅ 生产库核查 + API：`接口测试考虑点【辅助作用】` id=6 visible，total=6

## 判决

**APPROVED**：进入一次总确认 → push → Draft PR → required checks → 合入 main。

## 下一批次 Leader 条件

- C108-1（P1）：Railway 部署环境增加 `KNOWLEDGE_INGEST_ENABLED=true` 后，复验生产 API capture：
  唯一内容→200+id、重复→409、开关关→503 明确提示；结果登记交付清单。
- C102-2（部分关闭）：capture 409 子项本批关闭；vector_search 非 functional 子项保持 Open。
- 沿用 C107-2（接口关联能力）、C103-5/6、C102-1/3/4/5、C99-1、C96-1、C95-1/C74-2、CP-C2/C84-1。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| capture 一律 409 是「开关关/重复/异常」混义误报，非去重逻辑缺陷 | 结果类型化 + 路由明确错误语义 + hooks 容错 | `ingest_service.py` + `knowledge.py` + 单测 |
| 生产环境开关未显式开启导致 API 不可用 | production.env(.example) 增加开关；Railway 人工步骤登记 | `config/runtime/production.env.example` + C108-1 |
| 规范文档已入库（C107-1） | 关闭 C107-1 与 C102-2 capture 子项 | C-CONDITIONS Closed 表 |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1d / 实际 0.5d | 0/0/1/0 | 0 | 配置+错误语义 | 部署环境开关先行探测；API 错误语义勿用单一业务码掩盖多种原因 |

**技能使用**：`cameltv-agent-team`、`test-case-design`。
