# Batch 108 — PRD（知识中心 capture 去重误判修复 + 规范导入闭环）

> **Product (🟦)** | Date: 2026-08-06 | Status: Review

```markdown
mode: full
豁免理由: 无（涉及后端入库结果语义/API 错误响应/配置变更，走完整六部门流水线）。
非目标: C107-2 接口关联能力；C103-5 真实样本批量采集；C103-6 AI 块级截断补全；
vector_search 非 functional 修复（C102-2 另一子项，本批聚焦 capture）；
Test5 内网；生产账号；性能采集优化（C99-1）；iOS 真机（CP-C2/C84-1）。
```

## 1. 问题陈述（C102-2 / C107-1，2026-08-06 实测）

**现象**：`POST /api/v1/knowledge/capture` 对唯一内容返回业务码 409「内容重复，已存在相同知识源」。

**生产实测证据（Batch 107 登记）**：
- 以 `sportsadmin` 调用 capture 导入「接口测试考虑点【辅助作用】」规范文档 → HTTP 200 + code 409「内容重复」；
- 直连生产库核查：`knowledge_source` 项目 1 共 5 条 capture（Batch 102 体育文档），**规范文档 content_hash（3a139c…）无任何匹配** → 非真实重复；
- 本地复现（临时 SQLite）：同标题同内容第二次入库返回 None（正确去重）、异内容可新建、开关关返回 None → **去重逻辑本身正确**。

**根因**：
1. `ingest_capture_in_new_session` 在 `knowledge_ingest_enabled=False` 时直接返回 `None`；部署环境（Railway）未开启该开关 → 每次 capture 都走 None 分支；
2. `capture_insight` 路由把 `None`（disabled / duplicate / 异常三种原因）**一律映射为 409「内容重复」**，误导排障；
3. `_post_ingest_hooks`（向量嵌入/图谱/Agent）若抛异常，会被 except 捕获并返回 None——即使源已 commit，也被误报为失败/重复。

**用户诉求（2026-08-06）**：修复 capture 去重误判，并把规范文档导入知识中心闭环（C107-1）。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| capture 错误语义 | 一律 409「内容重复」 | 区分：未启用（503+明确 msg）/ 重复（409）/ 内部失败（500+日志）/ 成功（200+id） |
| 入库结果可靠性 | hooks 失败翻转成功为 None | hooks 失败仅记日志，不影响已提交源的成功返回 |
| 配置对齐 | production.env 未显式开启 | `KNOWLEDGE_INGEST_ENABLED=true` 写入 production.env；部署清单登记 Railway env |
| 规范导入闭环（C107-1） | 知识中心无该文档 | `接口测试考虑点【辅助作用】.md` 入库，sources 列表可见 |
| 可回归 | 无专项单测 | 新增 capture 结果语义单测全绿；现有 knowledge 测试无回归 |

## 3. 用户故事 + 验收标准

- As a **QA/用户**, I want capture 报错能区分「未启用/重复/失败」，so that 不会把开关关闭误认为内容重复。
- As a **平台管理员**, I want 知识入库开关开启后 capture 正常入库，so that 规范文档可从知识中心检索。
- As a **验收负责人**, I want 规范文档出现在知识中心 sources 列表，so that C107-1 闭环。

Given 捕获内容与库中重复，When 调用 capture，Then 返回 409「内容重复」。
Given 知识入库开关关闭，When 调用 capture，Then 返回 503 且提示「知识入库未启用」。
Given 开关开启且内容唯一，When 调用 capture，Then 返回 200 + 新源 id，且 sources 列表可见。

## 4. 技术考量

- `ingest_service.ingest_capture_in_new_session` 返回类型改为结构化结果 `CaptureIngestResult(reason, source_id)`：
  `created` / `disabled` / `duplicate` / `error`，不再用 None 混义。
- `knowledge.py::capture_insight` 按 reason 映射：disabled→HTTP 503；duplicate→HTTP 409「内容重复」；
  error→HTTP 500（记录日志）；created→200 + id。
- `_post_ingest_hooks` 调用包 try/except 仅记日志，入库成功不被 hooks 失败翻转。
- 配置：`config/runtime/production.env` 增加 `KNOWLEDGE_INGEST_ENABLED=true`（与 docker-compose 默认一致）；
  Railway 部署环境变量作为人工步骤登记到交付清单/Leader 条件（C106-1 同款模式）。
- 闭环导入：代码合入后以固定渠道（生产库直连 ingest，Batch 102/103 已授权通道）导入规范文档，
  再经 sources API 验证；部署后 API 路径随 Railway env 开启后复验。

## 5. 范围

**纳入**：capture 结果类型化 + 路由错误映射 + hooks 容错 + production.env 开关 + 单测 + 规范导入闭环 + 证据登记。
**非目标**（见头部）：C107-2、C103-5/6、vector_search 修复、Test5、生产账号、性能优化、iOS 真机。
