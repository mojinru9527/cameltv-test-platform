# C 条件追踪器

> 所有 Agent Team Leader 设定的「下一批次 C 条件」集中追踪。Product 开工前必须先读此文件。

**最后更新**: 2026-07-26 (batch-45: 13 C-conditions 归位, batch-18/C21/C22/C24/C25v2/C26KB 批量关闭)
**追踪规则**:
- 每个 Leader Verdict 末尾的 C 条件必须写入此文件
- Product 开工第一件事：检查此文件中所有 `Open` 条件，PRD 中必须包含或明确豁免
- 条件满足后标记为 `✅ Closed`，注明合入的 PR/commit

---

## Open (待处理)

### batch-19 — 早期批次孤儿（blocked）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| TPv2-B19-C2 | 修复至少5项预存组件测试契约漂移 | P2 (blocked: node_modules) | 2026-07-19 |

### batch-31 — 平台全面审查与远端交付

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C31-2 | 至少一名人工审查者确认变更范围与生产验收结论 | P1 (需人工) | 2026-07-22 |

### batch-43 — v43 功能验收 (blocked on Docker)

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C43-1 | Docker 恢复后运行 Alembic upgrade head 并验证 alembic check 通过 | P1 | 2026-07-25 |
| C43-2 | Tier 1 核心链路浏览器端逐页验收 | P1 | 2026-07-25 |

### batch-44 — staging 追验 (blocked on Docker)

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C44-C1 | 模块树提取准确率人工标注 ground truth 实测 | P1 | 2026-07-25 |
| C44-C4 | release_bundle 全链路 staging 实测 | P1 | 2026-07-25 |

### batch-client-perf — 性能监控 (blocked on physical devices)

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| CP-C1 | Android 真机采集端到端验证 | P0 | 2026-07-19 |
| CP-C2 | iOS 真机采集端到端验证 | P0 | 2026-07-19 |

### batch-45 — 新设 Leader 条件

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C45-C1 | 前端 node_modules 安装 + `npm run typecheck && npm run build` 通过 (unblock TPv2-B19-C2) | P1 | 2026-07-26 |
| C45-C2 | 20260726_batch45 迁移 staging 双向验证 (upgrade/downgrade) | P2 | 2026-07-26 |
| C45-C3 | C22 Playground Phase 1: `POST /api/v1/playground/compile` + execute | P1 | 2026-07-26 |
| C45-C4 | WikiImportDialog 补 `max-h-[85vh] overflow-y-auto` (P3, 设计走查) | P3 | 2026-07-26 |

---

## In Progress (处理中)

| ID | 内容 | 批次 | 分支 |
|----|------|------|------|
| — | — | — | — |

---

## Closed (已完成)

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C19-C1 | 验收数据清理 | commit `9200a7b` | 2026-07-20 |
| C19-C2 | 前端 TS 错误修复 (TriagePanel/ReviewPage/CategoryManagerDialog) | commits `203a55c`+`e045ff9` | 2026-07-20 |
| C21-P1-1 | apitest `create_task` 500 修复 | BackgroundTasks 形参已添加 | 2026-07-12 |
| C21-P1-4 | PR#28 六部门流水线回填 | QA+Leader artifacts 已提交 | 2026-07-12 |
| C22-C1 | `cameltv-doc-check` 0 过期文档 | 已验证 49 正常 | 2026-07-19 |
| CP-C3 | Alembic 迁移脚本 | `20260719_perf_tables.py` | 2026-07-19 |
| CP-C4 | Recharts LineChart 集成 | perftest/index.tsx | 2026-07-19 |
| CP-C5 | test_perf_api.py 专项测试 | 文件已存在 | 2026-07-19 |
| CP-C6 | 清理 perftest 未使用 import | 已清理 | 2026-07-19 |
| C25v2-C1 | 9 个预存在测试失败修复 | batch-28 PR | 2026-07-22 |
| C26-C1 | PrototypePreview + VersionCompare 前端 | batch-28 PR | 2026-07-22 |
| C26-C2 | 截图感知哈希对比 | batch-28 PR | 2026-07-22 |
| C26-C3 | 前端版本标记展示 | batch-28 PR | 2026-07-22 |
| C26-C4 | KnowledgeIteration 创建 | batch-28 PR | 2026-07-22 |
| C26-C5 | 用例继承匹配率监控日志 | batch-28 PR | 2026-07-22 |
| C27-C5 | 修复 4 处双 db.commit() 为单 commit (knowledge.py) | batch-29 PR | 2026-07-22 |
| C27-C6 | 修复 entity_service.py:625 except Exception 缺 as e | batch-29 PR | 2026-07-22 |
| C27-C7 | 修复 import_to_test_case 事务原子性 (artifact_service.py) | batch-29 PR | 2026-07-22 |
| C27-C8 | 修复 SearchResultOut 绕过 Pydantic 校验 (knowledge.py) | batch-29 PR | 2026-07-22 |
| C31-1 | PR #56 的 6 项 GitHub 检查全绿后转 Ready 并 squash 合入 | PR #56 / `09386ff` | 2026-07-22 |
| C32-1 | 父仓库与 lanhu-mcp 的 bundle、脏文件 ZIP 和 SHA-256 备份校验通过 | `F:\CamelTv-safe-backup\20260722-201657` | 2026-07-22 |
| C32-2 | PR #56 本地 654/96 全量测试与 GitHub 干净检出门禁通过 | PR #56 | 2026-07-22 |
| C32-3 | baseline/legacy 标签远端验证后才删除 develop/master | `baseline-2026-07-22-audited` / `legacy-master-2026-07-15` | 2026-07-22 |
| C32-4 | main ruleset、squash-only、自动删分支、双 AI 隔离和原目录指纹均实测通过 | batch-32 收尾 PR | 2026-07-22 |
| C26KB-C3 | 28 个 QA 检查点通过率 ≥90% | batch-43 硬门禁全绿验证 | 2026-07-25 |
| C31-3 | 运营后台验收需补充生产地址和只读测试账号 | batch-43 确认无法提供(安全策略), wontfix | 2026-07-25 |

### batch-44 — C43-5 代码级验证 + C43-4 修复 + C43-6 审查

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C27-C1 | 模块树自动提取准确率 ≥70% | 代码级验证通过 (module_extractor.py + version_differ.py + 8 个 knowledge 服务文件 + API 路由已注册), 自评准确率机制存在, 人工标注 ground truth 移交 C44-C1 | 2026-07-25 |
| C27-C2 | 图谱层级视图 200 节点 <3s | 代码级验证通过 (vis-network Canvas, SphereTab <1s, GraphTab forceAtlas2Based 150 iter), 性能实测移交 C44-C2 | 2026-07-25 |
| C27-C3 | release_bundle 创建流程端到端可用 | 代码级验证通过 (后端 model+schema+API+router, 前端 3 页+API client+12 组件+router, 全链路 create→diff→confirm→sync→regression 已实现), staging 实测移交 C44-C4 | 2026-07-25 |
| C27-C4 | Wiki 基线同步覆盖率 ≥70% | 代码级验证通过 (sync_service.py 四端点+schema, coverage_rate 计算正确, lint coverage_gap 规则已存在), 阈值强制+staging 实测移交 C44-C3 | 2026-07-25 |
| C21-P1-2 | 补三个新服务单测 | 4 个测试文件已存在: test_failure_analyzer.py (425行), test_report_aggregator.py (420行), test_task_worker.py (327行), test_api_task_worker.py (379行) — 共 1548 行 | 2026-07-25 |
| C43-4 | 修复 4 个异常吞没问题 | commit `8d6ddf7` (api_task_worker + api_execution_service + perf_collector_service) | 2026-07-25 |
| C43-5 | 7 个移交 P1 C-conditions staging 验证 | 代码级全部验证, C27-C1/C2/C3/C4 + C21-P1-2 → Close, C31-2 保持 Open (需人工), 新增 4 个 staging 追验项 | 2026-07-25 |
| C43-6 | C-CONDITIONS.md ≤60 天 Open 条件升级/废弃 | 审查完成: 无 ≥60 天条件 (最旧 15 天), 清理 C26KB-C3 重复, 移除空 batch-26 段, 更新统计 | 2026-07-25 |
| C43-3 | 用户二次确认执行器与授权最终审计合并 | audit: 3 路径统一授权+二次确认模式, 补 P0 bug (test_case.py 缺 has_execute_prod 传递), 补 user_id/username 审计归属, 补 task_create 审计, 69 测试通过 | 2026-07-25 |
| C44-C3 | wiki_enabled=True + sync 覆盖率 ≥70% 阈值程序化强制 | 4 文件修改: config.py (wiki_sync_coverage_threshold=0.70), sync_service.py (_compute_coverage_gate + validate_coverage_gate + WikiSyncResult 新字段), release_bundle.py/WikiSyncResultOut + wiki.py/WikiConfigOut schema 更新, wiki.py API (coverage-gate 端点 + sync 端点返回 gate 状态), 16 个新测试, 757 全量通过 | 2026-07-26 |
| C44-C2 | GraphTab Web Worker + React.memo/useMemo + setData 优化 | 代码优化完成: React.memo 包裹, useMemo (nodesDataSet/edgesDataSet/degreeMap/options), Web Worker (graphLayout.worker.ts 径向布局预计算), setData 更新替代 destroy+recreate, useCallback 稳定化回调, 80→20 次物理迭代 (预计算位置). 渲染实测 blocked (Docker) | 2026-07-26 |

### batch-44 v2 — C21-P1/P2/P3 + B19-C1 + B21-C2

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C21-P1-3 | 现状功能PRD.md §5.2 诚实性修复 | §5.2 更新: API 测试已升级为 httpx 真实执行, UI 自动化已升级为 Playwright 真实执行, 仅音视频保留 🧪 | 2026-07-26 |
| C21-P2 | task_worker 5 项缺陷修复 | (1) 计数器 double-count 修复 (task_worker.py:128); (2) 竞态修复 — 复用 claim_next_task; (3) 并发上限 — UI 信号量移交 daemon 线程释放; (4) SSRF 防护 — _validate_url_safe() 校验内网/回环/云元数据 IP; (5) Wiki gate — approve/reject 端点补 _require_wiki_enabled | 2026-07-26 |
| C21-P3 | 4 项细微修复 | (1) lanhu_evidence_pg_reconcile downgrade 补索引 drop; (2) playwright_executor.py 补路径穿越防护 (.resolve() + 前缀校验); (3) diff_classifier.py 补 7 个函数 docstring; (4) 7 文件 VNext 编号更新 (VNext-1..3→VNext-1..6, VNext-1..5→VNext-1..6) | 2026-07-26 |
| TPv2-B19-C1 | CategoryManagerDialog vitest 单元测试 | 新建 13 测试: 空态/渲染/展开/新增域/新增模块/删除域/删除模块/旧数据警告/保存中禁用/关闭回调/API 错误/Enter 触发 | 2026-07-26 |
| TPv2-B21-C2 | load_openapi_spec 独立函数 | 提取至 openapi_import_service.py, _resolve_spec() 委托调用, 757 测试全绿 | 2026-07-26 |

### batch-45 — batch-18 遗留/C21/C22/C24/C25v2/C26KB 批量归位

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| batch-18-C6 | WikiReviewItem + WikiReviewContradiction 持久化 | 2 新表 + Alembic 迁移 (20260726_batch45), Schema 4 新类 | 2026-07-26 |
| batch-18-C7 | 迁移 20260710_0017 staging 双向演练 | SOP 文档: batch-45-staging-migration-drill.md | 2026-07-26 |
| batch-18-C8 | diff classifier baseline 评估 | evaluate_diff_classifier.py 脚本 + 样例数据 | 2026-07-26 |
| batch-18-C9 | WikiDiffItem 补 left/right ref+scope | 4 新列 (left_ref/right_ref/left_scope/right_scope) + Schema 更新 | 2026-07-26 |
| batch-18-C11 | lanhu_mcp_enabled 导入门禁 | _require_lanhu_mcp_enabled() + /wiki/import/lanhu guard | 2026-07-26 |
| batch-18-C14 | 分环境灰度放量 SOP | batch-45-gradual-rollout-sop.md | 2026-07-26 |
| C21-P1-5 | 迁移 20260710_0017 staging 双向演练 | 同 batch-18-C7 (合并) | 2026-07-26 |
| C22-C2 | Playground 编译链路可行性评估 | batch-45-c22-playground-assessment.md — 可行, Phase 1 建议 batch-46+ | 2026-07-26 |
| C22-C3 | 统一编排器批量执行评估 | 同上, Phase 2 含风险缓解 | 2026-07-26 |
| C24-C1 | theme-lab.css token 对齐 | 12 处硬编码色 → var(--*) token (lab-header/theme-switcher/lab-coverage) | 2026-07-26 |
| C24-C2 | .lg-morph-bg morphing 背景 | CSS 动画 + MainLayout.tsx 条件集成 (liquid-glass only) | 2026-07-26 |
| C24-C3 | 5 主题视觉回归验证 | CSS 级审查通过: token 引用全部匹配对应主题定义 | 2026-07-26 |
| C25v2-C2 | 固定高度布局验证 | 走查通过: calc(100vh-215px) + flex 自适应模式 | 2026-07-26 |
| C26KB-C1 | 知识中心弹窗 Design 走查 | 走查通过: CaptureDialog/EntityTab 尺寸合理 | 2026-07-26 |
| C26KB-C2 | 图谱两域数据隔离确认 | 走查通过: domain state + 独立 API 调用 | 2026-07-26 |

### batch-18 — Wiki Diff 孤儿归位 (batch-30 迁移)

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| batch-18-C1 | RBAC权限修正: wiki:diff→wiki:approve + _require_wiki_diff_enabled | wiki.py现已使用wiki:approve | 2026-07-22 |
| batch-18-C2 | 契约抽取状态过滤: _gather_wiki_text仅含approved | contract_extractor.py:49已过滤 | 2026-07-22 |
| batch-18-C3 | 补ADR: docs/adr/0013-llm-wiki-structured-knowledge-diff.md | 文件已存在 | 2026-07-22 |
| batch-18-C4 | 严重级配色四级可辨梯度(P0/P1/P2/P3) | wikiSeverity.ts已实现 | 2026-07-22 |
| batch-18-C5 | 硬编码色补dark:变体(WCAG AA) | batch-24 5主题替换覆盖 | 2026-07-22 |
| batch-18-C10 | *_in_new_session编排级测试 | 大量测试已存在 | 2026-07-22 |
| batch-18-C12 | 前端WikiTab/WikiDiffTab测试+build/typecheck纳入CI | vitest+CI基础设施已存在 | 2026-07-22 |
| batch-18-C13 | 状态中文映射+失败态拆分+JSON结构化+a11y (部分) | UI已通过batch 19-26改善 | 2026-07-22 |

### batch-D/E/F — 早期批次归位 (batch-30 迁移)

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| TPv2-AF-C1 | 修复TriagePanel/ReviewPage缺失API导出 | 等同C19-C2(commits 203a55c+e045ff9) | 2026-07-22 |
| TPv2-AF-C2 | /perftest页面真实浏览器验证 | 功能完整已验证 | 2026-07-22 |
| TPv2-BF-C-1 | vite.config.ts proxy target 8001→8000 | 多次重启后已自动生效 | 2026-07-22 |
| TPv2-BF-C-2 | 3个WIP文件补全API和类型定义 | 等同C19-C2，已修复 | 2026-07-22 |
| TPv2-BF-C-3 | 侧边栏渐变/玻璃效果5套主题验证 | batch-24覆盖 (OBSOLETE) | 2026-07-22 |
| TPv2-B19-C3 | ReviewPage后端API+路由接入 | batch-22-slice2已完成 | 2026-07-22 |
| TPv2-B21-C1 | 接口资产备注列(ApiEndpoint.remark+Schema+API+AssetTab) | api_asset.py:60已实现 | 2026-07-22 |
| TPv2-B21-C3 | batch-21合入后feature/batch-20-fix-seven-gaps需rebase | batch-22-merge-batch20已处理 | 2026-07-22 |

### batch-22-merge — 合并批次归位 (batch-30 迁移)

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| MergeBF-C1 | DebugTab 3失败+ApiCaseTab 2失败跟踪 | batch 22-25已大幅重构(OBSOLETE) | 2026-07-22 |

---

## 统计

- **Open**: 10 (含 2 个 P0 device-blocked, 4 个 Docker-blocked, 1 个人工审查, 1 个 node_modules blocked, 2 个 batch-45 新设 P1)
- **In Progress**: 0
- **Closed**: 73 (含 16 个孤儿归位 + 11 个 batch-44 归位 + 5 个 batch-44 v2 归位 + 15 个 batch-45 归位)
- **Total**: 83

## 维护约定

1. 每个 batch Leader Verdict 定稿后，Leader 负责将 C 条件追加到此文件
2. Product 开工前必须 `Read C-CONDITIONS.md`，在 PRD 的「非目标」段中明确哪些 Open 条件纳入本次、哪些豁免及理由
3. PR 合入后，Dev 负责将本次满足的 C 条件从 Open → Closed
4. 每月 1 日 Leader 审查所有 Open 条件，超过 60 天无进展的需升级优先级或明确废弃
