# Batch 91 — QA 报告（Open 区可本地处理项收口）

> **QA (🔍)** | Date: 2026-08-05 | Verdict: PASS（C26KB-C3 部分达标，缺口转 batch-94）

## 测试总览

| 条件 | 通过 | 失败/缺口 | 阻塞 |
|:-----|:----:|:--------:|:----:|
| C90-1 统计脚本口径 | ✅ | 0 | 0 |
| C90-2a C21-P3 四子项 | ✅ 4/4 | 0 | 0 |
| C90-2b batch-18-C14 SOP | ✅ | 0 | 0 |
| C26KB-C3 检查点复核 | 25/28（89.3%） | 3（C7 批量操作） | 0（缺口转 batch-94） |

## 可执行门禁

| # | 门禁 | 命令 | 退出码 | 结果 |
|---|------|------|:------:|------|
| G1 | C 条件审计 | `audit-cconditions.ps1` | 0 | 硬错 0；stats: Open=25 (deferred=18) Closed=121 |
| G2 | 迁移测试 | `pytest test_alembic_runbook/test_migration_revision_ids/test_batch48_requirement_migration` | 0 | 7 passed |
| G3 | 文件范围 | 本批仅 scripts/git + docs + C-CONDITIONS + work-logs | — | 无生产代码变更 |

## 逐条件验证

### C90-1：统计脚本口径（✅）
- `audit-cconditions.ps1` 新增 `Get-ConditionStats` + `stats:` 输出（Open/Closed/Deferred 按文件实际解析，跳过分隔行/区分 Deferred 节）
- 输出与文件一致：Open=25（rows=25, deferred=18）Closed=121
- C-CONDITIONS「维护约定」第 0 条强制引用脚本口径

### C90-2a：C21-P3 四子项（✅ 4/4）

| 子项 | 证据 |
|------|------|
| migration downgrade | `test_alembic_runbook.py` 覆盖安全 upgrade/downgrade + 禁止相对回退（`downgrade -1`）；实测 7 passed |
| playwright path traversal | `lanhu_evidence.py:315` / `ui_test.py:55` `is_relative_to(base)` 守卫 |
| diff_classifier docstring | `services/wiki/diff_classifier.py` 模块 docstring（12 维/差异类型/严重级别/evidence） |
| VNext-N 编号 | `docs/LLM-Wiki知识库差异对比能力落地方案.md` VNext-1..6 编号约定 |

### C90-2b：灰度放量 SOP（✅）
- `docs/灰度放量SOP.md`：环境分层 / 发布前置检查 / 灰度节奏（观察窗口 + 比例建议）/ 回滚（Vercel/Railway/alembic）/ 24h 检查清单 / 责任矩阵

### C26KB-C3：知识中心 28 检查点（25/28 = 89.3%，未达 90%）

**通过 25 项**（代码锚点 + 既有截图证据）：
- C1 弹窗交互 4/4（ProjectTab Dialog + 内容 + 尺寸 + 关闭）
- C2 PlatformTab 分区折叠 5/5（togglePartition/Chevron + 点击弹窗 + 一致性）
- C3 Tab 导航 3/3（概览默认 + 顺序 + URL 参数）
- C4 搜索 3/3（常驻栏 + 回车 + 全状态检索：search_service 无 status 过滤）
- C5 图谱 3/3（默认项目域 + 切换 + knowledge.py knowledge_domain 域过滤）
- C6 弹窗 UI 4/4（内容弹窗 7xl/95vw；文字 text-sm；Select position=popper；overflow-y-auto）
- C8 溯源 3/3（module_name 字段 + SourceListTab 项目→模块→来源 链路）

**未通过 3 项（C7 批量操作）**：ArtifactReviewTab 仅单条采纳/驳回/导入（按钮逐条），无勾选批量机制 → 批量采纳/批量驳回/批量导入 3 检查点未实现。

**结论**：C26KB-C3 保持 Open；缺口=AI 产物批量审核/采纳 UI，与 batch-94「用例生成批量审核/采纳工作流 UI」同源，落地后复测。

## 缺陷与遗留

| # | 级别 | 内容 | 处理 |
|---|:----:|------|------|
| B91-Q1 | P2 | 知识中心 AI 审核台缺批量采纳/驳回/导入（C7 3 项检查点） | 转 batch-94 实现 + C26KB-C3 复测 |
| B91-Q2 | P3 | search_service.py 模块 docstring 仍写「仅 status=active」与实现不符（已不过滤） | 顺手可修文案（不阻断） |

## 发布建议

状态：**READY**（本批四项收口完成；C26KB-C3 按证据保持 Open 并转批）。

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1d / 实际 0.5d | 0/0/1/1 | 0 | 需求缺口 | 验收批先核对检查点与实现是否匹配，避免“清单在、功能缺” |

**技能使用**：`cameltv-agent-team`、`audit-cconditions.ps1`、`playwright-skill`（知识中心截图引用）
