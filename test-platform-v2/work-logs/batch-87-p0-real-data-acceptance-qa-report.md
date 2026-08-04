# Batch 87 — QA 报告（P0 真实数据验收）

> **QA (🔍)** | Date: 2026-08-04 | Verdict: PASS（有条件的部分闭环）

## 测试总览

| Slice | 通过 | 失败 | 阻塞 |
|:------|:----:|:----:|:----:|
| 1 凭据核验（AI/蓝湖/OCR） | 1 | 0 | 1（蓝湖真实链接待用户） |
| 2 Knowledge/Wiki/Trace 真实数据闭环 | 1 | 0 | 1（Wiki 蓝湖设计源 ingest） |
| 3 真实 UI 主链（用例→计划→执行→报告/定时/缺陷） | 1 | 0 | 0 |
| 4 J03/J08/J19 矩阵 | 1 | 0 | 0 |

## 可执行门禁

| # | 门禁 | 方式 | 结果 |
|---|------|------|------|
| G1 | 本批无代码改动 | 纯验收/证据批（未改 app/tests） | 不适用（注明）；后端/前端回归无受影响面 |
| G2 | scan-common-bugs | `scan-common-bugs.ps1` | 执行确认（见下） |
| G3 | audit-cconditions | `audit-cconditions.ps1 -RequireLatestBatch` | 0 硬错（见下） |

## Slice 1 — 凭据核验（真实链路）

- DeepSeek：`GET /v1/models` → **200**（deepseek-v4-flash / deepseek-v4-pro），AI key 生效（不回显）。
- 蓝湖：`wiki/config` → lanhu_mcp_enabled=true；真实设计源导入需蓝湖链接 → **待用户提供**（C87-1）。
- OCR：本地 PaddleOCR（LANHU_OCR_PROVIDER=local），随蓝湖流程使用。

## Slice 2 — Knowledge/Wiki/Trace 真实数据闭环（C55-3/G56-011 主体）

| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 真实需求文档 | ✅ | 真实业务 docx（37KB，直播/回放/互动三功能）上传入库 |
| 真实 AI 提取 | ✅ | Stage1 extract 19.9s → 3 模块多功能点（真实 DeepSeek，非 fallback） |
| 真实 AI 用例生成 | ✅ | generate 28.6s → 25 条 functional_cases（按域分布 10/7/8） |
| 用例落库 | ✅ | import 25/25 → test_case 表 total=25 |
| RAG 检索 | ✅ | `/knowledge/search` → 命中真实 requirement_rule chunk（embedding BAAI/bge-small-zh，vector_search functional） |
| Trace 覆盖率 | ✅ | `/trace/coverage` total_cases=25；`/trace/requirement/1` imported_count=25 |
| 跨项目隔离 | ✅ | 项目 B 访问 A 的需求/用例/计划/报告/缺陷 → 全 403 |
| 事务/负面 | ✅ | 空文件 400「上传文件不能为空」；坏 xlsx 400「内容损坏或无法解析」 |
| 审计 | ✅ | `/system/audit-logs` 返回真实记录（project:member:add 等） |
| Wiki 蓝湖设计源 ingest | ⏳ | 需真实蓝湖链接走证据包质量门禁（J06 外部，C87-1） |

## Slice 3 — 真实 UI 主链（C55-4/G56-012）

| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 真实执行 | ✅ | 计划挂 25 条真实用例，25/25 执行记录 pass（stats 25/25） |
| 报告 | ✅ | RP-20260804-001 生成 + xlsx 导出（7691B） |
| 定时任务 | ✅ | 计划任务创建 + trigger（run 生成） |
| 缺陷生命周期 | ✅ | 新建→confirmed→fixing→pending_review→closed 全链路 + 评论 |
| 真实 UI 渲染 | ✅ | Playwright 登录后 /testplan、/report、/defect、/schedule 均显示真实数据（截图 7 张） |
| 通知 | ⏳ | 真实 SMTP 收件未验（外部邮箱，C87-2） |

## Slice 4 — J03/J08/J19 矩阵（G56-014 增量）

| 项 | 结果 |
|---|------|
| J03 角色/用户 CRUD | ✅ create/update/delete role 200；撤权后访问 403 |
| J08 搜索/坏文件 | ✅ 关键词「直播」→ 17 条；坏 xlsx → 400 |
| J19 IDOR | ✅ 6 类资源跨项目全 403（隔离）；分页 total 一致（25=25，10/页） |
| J09 真实 UI 链 | ✅ 已由 Slice 3 覆盖 |
| J15/J16 | 引用 batch-74 基线（已闭环） |

## 缺陷与遗留

| # | 级别 | 内容 | 处理 |
|---|:----:|------|------|
| B87-Q1 | P2 | 项目 B 成员（tester 角色）在自身项目无 `testcase:create` 权限（403「缺少权限」）——项目级角色权限疑似未生效 | 登记 C87-3，下批修复/核验 |
| B87-Q2 | P3 | Wiki 真实设计源 ingest 需蓝湖链接；SMTP 真实收件需邮箱 | 登记 C87-1/C87-2（外部） |

## CI 分层核对

- 本批零代码改动（仅验收证据 + 文档 + C-CONDITIONS）；CI 按 docs 域跳过前后端重测，本地亦无受影响测试面。

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 6h / 实际 4h | 0/0/1/2 | 0 | 外部依赖 | P0 验收前先核对外部凭据/链接清单，明确哪些需用户提供再排期 |
