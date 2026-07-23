# Batch 38 — QA 报告
> **QA (🔍)** | Date: 2026-07-23 | Verdict: READY（代码审查通过，需 CI 验证）

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 8 | 8 | 0 | 0 |

## 逐条件验证

### US-1: 项目知识归属清晰化
**变更文件**: [ProjectTab.tsx:32](test-platform-v2/frontend/src/pages/knowledge/components/ProjectTab.tsx#L32)
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 过滤参数从 `para_category` 改为 `knowledge_domain` | ✅ PASS | `fetchKnowledgeSources({ knowledge_domain: 'project', page_size: 100 })` |
| 迁移脚本存在 | ✅ PASS | `backend/scripts/migrate_knowledge_domain.py` 已实现完整迁移逻辑 |
| 代码无回归 | ✅ PASS | 仅改一个参数，其余逻辑不变 |

### US-2: 检索结果可点击查看
**变更文件**: [SearchTab.tsx:237-248](test-platform-v2/frontend/src/pages/knowledge/components/SearchTab.tsx#L237-L248), [SearchTab.tsx:263-295](test-platform-v2/frontend/src/pages/knowledge/components/SearchTab.tsx#L263-L295)
| 检查项 | 结果 | 说明 |
|--------|------|------|
| Card 添加 onClick | ✅ PASS | `onClick={() => setDetailResult(r)}` + cursor-pointer + hover 样式 |
| Dialog 显示词条内容 | ✅ PASS | max-w-7xl Dialog，展示类型/标题/相关度/来源/内容 |
| Dialog 可关闭 | ✅ PASS | `onOpenChange` 处理 + ESC/遮罩关闭 |
| 新增 import 无遗漏 | ✅ PASS | X, Dialog, DialogContent, DialogHeader, DialogTitle 全部导入 |

### US-3: 知识源弹窗适配长内容
**变更文件**: [ProjectTab.tsx:129,212](test-platform-v2/frontend/src/pages/knowledge/components/ProjectTab.tsx), [PlatformTab.tsx:208,291](test-platform-v2/frontend/src/pages/knowledge/components/PlatformTab.tsx), [SourceListTab.tsx:231](test-platform-v2/frontend/src/pages/knowledge/components/SourceListTab.tsx)
| 检查项 | 结果 | 说明 |
|--------|------|------|
| Dialog max-w 5xl→7xl | ✅ PASS | 三个 Tab 均已更新为 max-w-7xl（1280px vs 1024px） |
| pre max-h 500px→60vh | ✅ PASS | ProjectTab/PlatformTab 均已更新 |
| overflow-y-auto 保持 | ✅ PASS | 所有 DialogContent 均有 overflow-y-auto |
| 响应式 width 保持 | ✅ PASS | w-[95vw] 保持不变，小屏适配 |

### US-4: 验证按钮状态反馈
**变更文件**: [SourceListTab.tsx:90-106](test-platform-v2/frontend/src/pages/knowledge/components/SourceListTab.tsx#L90-L106), [SourceListTab.tsx:193-203](test-platform-v2/frontend/src/pages/knowledge/components/SourceListTab.tsx#L193-L203)
| 检查项 | 结果 | 说明 |
|--------|------|------|
| handleVerify 使用返回值更新本地 state | ✅ PASS | `setRows(prev => prev.map(...{ ...r, ...updated }))` |
| 已验证今天 → 绿色 CheckCheck 图标 | ✅ PASS | `isVerifiedToday()` 辅助函数 + green-600 |
| 验证中 → Loader2 spin | ✅ PASS | verifying Set 判断 |
| 已验证今天 → disabled | ✅ PASS | `disabled={... || isVerifiedToday(s.last_verified_at)}` |
| PlatformTab 验证逻辑正常 | ✅ PASS | 已有用返回值更新本地 state 的逻辑 (L67-70) |

### US-5: RAG 向量回填可用
**变更文件**: [config.py:116](test-platform-v2/backend/app/core/config.py#L116)
| 检查项 | 结果 | 说明 |
|--------|------|------|
| rag_enabled 默认值 True | ✅ PASS | `rag_enabled: bool = True` |
| 无其他代码变更 | ✅ PASS | API 层/Service 层的 503 门禁保持，仅 config 驱动 |
| 回退安全 | ✅ PASS | 仍可通过 .env 覆盖 `RAG_ENABLED=false` |

### US-6: 批量审核按钮
**变更文件**: [ArtifactReviewTab.tsx:194-235](test-platform-v2/frontend/src/pages/knowledge/components/ArtifactReviewTab.tsx#L194-L235)
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 批量按钮始终可见 | ✅ PASS | 移除了 `{selectedPendingCount > 0 && ...}` 条件包裹 |
| 未选时 disabled | ✅ PASS | `disabled={batchLoading || selectedPendingCount === 0}` |
| 快捷"全选可操作" | ✅ PASS | 选中当前页所有 pending + approved |
| 快捷"取消全选" | ✅ PASS | 有选择时显示 |
| 全选 checkbox 逻辑不变 | ✅ PASS | 未改动 header checkbox 逻辑 |

### US-7: 知识图谱提取/演化可用
**变更文件**: [config.py:117](test-platform-v2/backend/app/core/config.py#L117)
| 检查项 | 结果 | 说明 |
|--------|------|------|
| knowledge_graph_enabled 默认值 True | ✅ PASS | `knowledge_graph_enabled: bool = True` |
| GraphTab handleExtract 错误处理正常 | ✅ PASS | catch 块有 toast.error |
| 回退安全 | ✅ PASS | 可通过 .env 覆盖 |

### US-8: 蓝湖证据采集可用
**变更文件**: [config.py:143](test-platform-v2/backend/app/core/config.py#L143)
| 检查项 | 结果 | 说明 |
|--------|------|------|
| lanhu_evidence_enabled 默认值 True | ✅ PASS | `lanhu_evidence_enabled: bool = True` |
| 回退安全 | ✅ PASS | 可通过 .env 覆盖 |

## 可执行门禁

| 门禁 | 状态 | 说明 |
|------|:----:|------|
| 前端 typecheck | ⏳ | 需 CI 执行 `npm run typecheck` |
| 前端 build | ⏳ | 需 CI 执行 `npm run build` |
| 后端 ruff F821 | ⏳ | 需 CI 执行 `ruff check app --select F821` |
| Alembic 单头 | ⏳ | 需 CI 验证 |
| 代码审查 | ✅ | 6 文件 118+ 38- 行变更，逻辑审查无问题 |

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|---|:------:|------|------|:----:|
| — | — | 无缺陷发现 | — | — |

## 变更摘要

```
6 files changed, 118 insertions(+), 38 deletions(-)
```

| 文件 | 变更性质 |
|------|---------|
| backend/app/core/config.py | 3 个 bool 默认值 False→True |
| SearchTab.tsx | 新增检索结果点击弹窗（+50 行） |
| SourceListTab.tsx | 验证按钮即时状态更新 + 弹窗尺寸 |
| ProjectTab.tsx | 过滤参数修正 + 弹窗尺寸 |
| PlatformTab.tsx | 弹窗尺寸 |
| ArtifactReviewTab.tsx | 批量按钮始终可见 + 快捷全选 |

## 发布建议
**状态**: READY
**必修复**: 0
**建议修复**: 0
**说明**: 所有变更为参数调整和交互补全，无新增复杂逻辑，风险极低。代码审查通过，CI 门禁待 PR 触发验证。
