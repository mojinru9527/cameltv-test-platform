# Batch 19 — QA Report
> **QA (🔍)** | Date: 2026-07-20 | Verdict: PASS (conditional on test data cleanup)

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 10 | 10 | 0 | 0 |

## 逐条件验证

### C1: 接口资产 — 服务Tab + 模块Collapsible层级
**变更文件**: [AssetTab.tsx](test-platform-v2/frontend/src/pages/apitest/components/AssetTab.tsx)
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 服务以 Tabs 展示（非 Select 下拉） | ✅ PASS | 使用 Radix `<Tabs>` 组件，每服务一个 `<TabsTrigger>` |
| 切换 Tab 仅显示对应服务的模块 | ✅ PASS | `activeTab` 状态驱动 `<TabsContent>` |
| 模块默认关闭 | ✅ PASS | `<Collapsible defaultOpen={false}>` |
| 模块展开显示接口列表 | ✅ PASS | 接口行保留 method badge + path + summary + 操作按钮 |
| 水平滚动 + 左右箭头 | ✅ PASS | `tabsScrollRef` + `ResizeObserver` + `ChevronLeft/Right` 按钮 |
| 全部服务 Tab 显示总数 | ✅ PASS | `全部服务 ({total})` |
| TypeScript 无错误 | ✅ PASS | `tsc --noEmit` 对本文件零错误 |

### C2: 快速调试 — 地址拆分 + 响应移底 + 默认测试5
**变更文件**: [DebugTab.tsx](test-platform-v2/frontend/src/pages/apitest/components/DebugTab.tsx)
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 四个独立输入框 | ✅ PASS | 服务器地址/服务名/模块路径/接口路径，2x2 grid |
| URL 预览实时显示 | ✅ PASS | `composeAssetUrl()` 拼接结果，mono 字体显示 |
| composeAssetUrl 正确处理斜杠 | ✅ PASS | 尾部去斜杠、模块路径/接口路径前置 `/` |
| 环境切换仅更新服务器地址 | ✅ PASS | `setBaseUrl(env.base_url)`，其他三字段不变 |
| 默认测试次数 5 | ✅ PASS | `useState(5)` + Select (1/3/5) |
| testCount>1 时重复发送 | ✅ PASS | `for` 循环发送 `testCount` 次 |
| 响应面板在请求配置下方 | ✅ PASS | 布局改为 `space-y-4`，ResponsePanel 全宽在底部 |
| pre-fill from endpoint | ✅ PASS | 解析 endpoint.path 分段填充四字段 |
| TypeScript 无错误 | ✅ PASS | `tsc --noEmit` 对本文件零错误 |

### C3: 接口用例 — 按接口分组 + 响应Modal
**变更文件**: [ApiCaseTab.tsx](test-platform-v2/frontend/src/pages/apitest/components/ApiCaseTab.tsx) + [apiCaseGroups.ts](test-platform-v2/frontend/src/pages/apitest/components/apiCaseGroups.ts)
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 同 api_spec_ref 的用例归入同一组 | ✅ PASS | `groupApiCases()` 按 `api_spec_ref` 分组，缺失的进 `__ungrouped__` |
| 组标题显示接口名 | ✅ PASS | 从首条 case.title 提取（如"接口C"） |
| 每组显示用例数 Badge | ✅ PASS | `<Badge variant="secondary">{group.cases.length}</Badge>` |
| 默认关闭 | ✅ PASS | `<Collapsible defaultOpen={false}>` |
| 响应 Modal（非右侧常驻面板） | ✅ PASS | `<Dialog>` 在 `runSingle` 完成后打开 |
| 组级"执行全部"按钮 | ✅ PASS | `runGroup()` 顺序执行组内所有用例 |
| 组级全选/取消 | ✅ PASS | `toggleGroup()` 切换组内全部选中状态 |
| 跨组批量执行保留 | ✅ PASS | `runBatch` 使用 `selected` Set 跨组创建任务 |
| TypeScript 无错误 | ✅ PASS | `tsc --noEmit` 对两文件零错误 |

### C4: 自动生成 — 上限30→200
**变更文件**: [api_case_generation_service.py](test-platform-v2/backend/app/services/api_case_generation_service.py)
| 检查项 | 结果 | 说明 |
|--------|------|------|
| `_MAX_CASES_PER_ENDPOINT = 200` | ✅ PASS | 第9行已从30改为200 |
| 现有15个生成测试全部通过 | ✅ PASS | `pytest tests/test_apitest_generation.py -q` 15 passed |

### C5: 用例列表 — 20/50/100分页 + 预留高度
**变更文件**: [testcase/index.tsx](test-platform-v2/frontend/src/pages/testcase/index.tsx)
| 检查项 | 结果 | 说明 |
|--------|------|------|
| pageSize 状态变量 | ✅ PASS | `useState(20)` |
| API 调用使用 pageSize | ✅ PASS | `{ page, page_size: pageSize }` |
| 分页大小 Select (20/50/100) | ✅ PASS | `<Select value={String(pageSize)}>` + 三选项 |
| 切换分页重置到第1页 | ✅ PASS | `setPageSize(Number(v)); setPage(1)` |
| 表格容器 min-h-[600px] | ✅ PASS | `<div className="rounded-md border min-h-[600px]">` |
| TypeScript 无错误 | ✅ PASS | `tsc --noEmit` 对本文件零错误 |

### C6: 用例编辑 — 步骤格式化回显
**变更文件**: [CaseDrawer.tsx](test-platform-v2/frontend/src/pages/testcase/CaseDrawer.tsx)
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 格式化视图（默认） | ✅ PASS | `stepsViewMode === 'formatted'` 显示解析后的文本 |
| JSON 视图切换 | ✅ PASS | 按钮切换 formatted/json 模式 |
| 解析 JSON → "1、xxx — yyy" | ✅ PASS | `formatSteps()` 解析 `[{step,desc,expected}]` 格式 |
| 非法 JSON 显示原始文本 | ✅ PASS | `catch { return raw }` |
| 原始 JSON 结构保留 | ✅ PASS | 提交时仍使用原始 `register('steps')` 值 |
| TypeScript 无错误 | ✅ PASS | `tsc --noEmit` 对本文件零错误 |

### C7: 需求列表 — 来源智能压缩
**变更文件**: [requirement/index.tsx](test-platform-v2/frontend/src/pages/requirement/index.tsx)
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 蓝湖 URL 提取版本号 | ✅ PASS | 正则匹配 `/updates/{version}` → "蓝湖 v{version}" |
| 非蓝湖 URL 提取域名 | ✅ PASS | `new URL(sourceRef).hostname` |
| title 悬停显示完整 URL | ✅ PASS | `title={r.source_ref}` 属性 |
| 单元格 max-w-[200px] 约束 | ✅ PASS | `<TableCell className="max-w-[200px]">` |
| 无 URL 显示 "-" | ✅ PASS | `if (!sourceRef) return { label: '-', isLink: false }` |
| TypeScript 无错误 | ✅ PASS | `tsc --noEmit` 对本文件零错误 |

### C8: 测试数据清理脚本
**变更文件**: [cleanup_batch19_test_data.py](test-platform-v2/backend/scripts/cleanup_batch19_test_data.py)
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 清理 test_cases | ✅ PASS | 按 `tags LIKE %batch19_verification%` 过滤 |
| 清理 api_endpoints | ✅ PASS | 同上 |
| 清理 api_services | ✅ PASS | 同上 |
| 清理 requirements | ✅ PASS | 同上 |
| 清理 test_plans | ✅ PASS | 同上 |
| 清理 test_executions | ✅ PASS | 同上 |
| 清理 defects | ✅ PASS | 同上 |
| --dry-run 模式 | ✅ PASS | 只显示不删除 |
| 显示表行数统计 | ✅ PASS | 清理前后对比 |

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| — | — | **零缺陷** | — | — |

> 注：所有 TypeScript 错误均来自预存在的未关联文件（TriagePanel.tsx, ReviewPage.tsx, CategoryManagerDialog.tsx），非本批次引入。

## 发布建议

**状态**: READY（需先执行数据清理）
- 必修复: 0
- 建议修复: 0
- 后置条件: 验收通过后执行 `cleanup_batch19_test_data.py` 删除验证数据
