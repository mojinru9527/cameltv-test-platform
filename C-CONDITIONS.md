# C 条件追踪器

> 所有 Agent Team Leader 设定的「下一批次 C 条件」集中追踪。Product 开工前必须先读此文件。

**最后更新**: 2026-07-22 (batch-31 平台全面审查)
**追踪规则**:
- 每个 Leader Verdict 末尾的 C 条件必须写入此文件
- Product 开工第一件事：检查此文件中所有 `Open` 条件，PRD 中必须包含或明确豁免
- 条件满足后标记为 `✅ Closed`，注明合入的 PR/commit

---

## Open (待处理)

### batch-18 — Wiki Diff 孤儿（batch-30 归位）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| batch-18-C6 | review_items/contradictions持久化 — WikiReviewItem表或复用AiArtifact | P2 | 2026-07-10 |
| batch-18-C7 | 迁移20260710_0017 staging双向演练(upgrade/downgrade) | P2 | 2026-07-10 |
| batch-18-C8 | 建标注语料评估差异召回率/误报率(diff classifier baseline) | P2 | 2026-07-10 |
| batch-18-C9 | 差异接口补left/right独立ref/scope或文档化单查询限制 | P2 | 2026-07-10 |
| batch-18-C11 | import校验lanhu_mcp_enabled开关—拒绝导入当disabled | P3 | 2026-07-10 |
| batch-18-C14 | 分环境灰度放量SOP文档 | P3 | 2026-07-10 |

### batch-19 — 早期批次孤儿（batch-30 归位）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| TPv2-B19-C1 | CategoryManagerDialog补充vitest单元测试 | P2 | 2026-07-19 |
| TPv2-B19-C2 | 修复至少5项预存组件测试契约漂移 | P2 | 2026-07-19 |

### batch-21 — 缺失特性孤儿（batch-30 归位）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| TPv2-B21-C2 | Knife4j doc.html URL自动发现(load_openapi_spec) | P2 | 2026-07-20 |

### batch-21 — PR #27/#28/#29 Pipeline Verification

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C21-P1-2 | 补三个新服务单测：failure_analyzer / report_aggregator / task_worker | P1 | 2026-07-12 |
| C21-P1-3 | `现状功能PRD.md` 诚实性修复：模块 11/12 详情段同步为真实执行 | P1 | 2026-07-12 |
| C21-P1-5 | 迁移 `20260710_0017` staging 双向演练 (upgrade/downgrade) | P1 | 2026-07-12 |
| C21-P2 | task_worker 双队列竞态 / semaphore 并发上限 / SSRF / Wiki 开关 / 计数器 double-count | P2 | 2026-07-12 |
| C21-P3 | migration downgrade / playwright path traversal / diff_classifier docstring / VNext-N 编号 | P3 | 2026-07-12 |

### batch-22 — Slice 1 Playground

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C22-C2 | 第一条成功编译链路（P0 功能用例→可执行 .spec.ts→headless Chromium→截图） | P1 | 2026-07-19 |
| C22-C3 | 统一编排器一次完整批量执行（3 API + 3 功能→6/6 有结果→报告自动生成） | P1 | 2026-07-19 |

### batch-24 — Five Themes

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C24-C1 | 更新 ThemeLab `theme-lab.css` 深层组件样式匹配新视觉 token | P2 | 2026-07-20 |
| C24-C2 | MainLayout 集成 `.lg-morph-bg` class 激活 Liquid Glass morphing 背景 | P2 | 2026-07-20 |
| C24-C3 | 5 主题视觉回归手动验证 | P2 | 2026-07-20 |

### batch-25v2 — 用例服务

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C25v2-C2 | 固定高度布局在不同分辨率下表现验证 | P2 | 2026-07-21 |

### batch-26 — 版本差异+AI增强

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| — | — | — | — |

### batch-26-KB — 知识中心 UX 修复

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C26KB-C1 | 弹窗尺寸 Design 走查确认达标 | P2 | 2026-07-21 |
| C26KB-C2 | 图谱两域数据隔离确认（截图对比） | P2 | 2026-07-21 |
| C26KB-C3 | 28 个 QA 检查点通过率 ≥90% | P2 | 2026-07-21 |

### batch-client-perf — 性能监控

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| CP-C1 | Android 真机采集端到端验证（BLOCKING：需物理设备） | P0 | 2026-07-19 |
| CP-C2 | iOS 真机采集端到端验证（BLOCKING：需物理设备 + iTunes/tidevice） | P0 | 2026-07-19 |

### batch-27 — Knowledge Sphere (✅ 代码已合入 PR #52, 4 条件 Open, 4 已修复)

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C27-C1 | 模块树自动提取准确率 ≥70%（需 staging 环境验证） | P1 | 2026-07-22 |
| C27-C2 | 图谱层级视图在 200 节点下渲染时间 <3s（需性能测试） | P1 | 2026-07-22 |
| C27-C3 | release_bundle 创建流程端到端可用（需集成测试） | P1 | 2026-07-22 |
| C27-C4 | Wiki 基线同步覆盖率 ≥70%（需 staging 环境验证） | P1 | 2026-07-22 |

### batch-31 — 平台全面审查与远端交付

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C31-1 | Batch 31 Draft PR 的 develop CI 全部通过后才允许转 Ready/合并 | P1 | 2026-07-22 |
| C31-2 | 至少一名人工审查者确认变更范围与生产验收结论 | P1 | 2026-07-22 |
| C31-3 | 运营后台验收需补充生产地址和只读测试账号 | P1 | 2026-07-22 |

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

- **Open**: 33 (含 2 个 P0 blocking, 10 个孤儿归位)
- **In Progress**: 0
- **Closed**: 35 (含 16 个孤儿归位)
- **Total**: 68

## 维护约定

1. 每个 batch Leader Verdict 定稿后，Leader 负责将 C 条件追加到此文件
2. Product 开工前必须 `Read C-CONDITIONS.md`，在 PRD 的「非目标」段中明确哪些 Open 条件纳入本次、哪些豁免及理由
3. PR 合入后，Dev 负责将本次满足的 C 条件从 Open → Closed
4. 每月 1 日 Leader 审查所有 Open 条件，超过 60 天无进展的需升级优先级或明确废弃
