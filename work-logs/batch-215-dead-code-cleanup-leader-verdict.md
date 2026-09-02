# Batch 215 — Leader Verdict：死代码清理（B5）
> **Leader (🎯)** | Date: 2026-09-03 | Decision: **APPROVED** | Executor: Codex | 完整批次

## 评审摘要
| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | 高 | 前端删除 4906 行、新增 252 行；引用审计零遗漏；保留项（api/playground、foolproof、有测试耦合组件）给出明确理由 |
| 风险 | 低 | 纯删除型清理；删除项可 git 回滚；未触碰后端 API / DB / 配置 |
| 覆盖 | 完整 | 路线图 B5 出口标准（rg 审计 + 全量 build/test）已核对 |

## 关键决策（已批准）
1. **删除 /testplan 独立页**（整页+自测）：入口已在 batch-212 下架，仅路由重定向 /testcase；数据只读归档随 batch-224。
2. **删除 Playground 独立页**：保留后端 `/api/v1/playground/*` 与前端 `src/api/playground.ts`（M1 场景执行复用），避免重复实现。
3. **删除无引用组件/Hook**（含 shadcn ui 原语、SphereTab、ApiDebugPanel 等 18+1）：引用审计 + typecheck/build/test 三重确认。保留 `components/foolproof/*`（B4 待接线）、`TriagePanel`（后续）、有测试耦合组件。
4. **special/perftest 冻结**：确认仅存于 `HIDDEN_MENU_CODES`（冻结=隐藏），README 已下架宣称。
5. **V1 工具退役**：代码已于 batch-98/100 移除，COMMANDS.md §5 标注退役，杜绝误导。
6. **根目录 `_tmp_*`**：.gitignore 兜底 + 删除 .pr-body-* + repo-boundaries 同步。
7. **根目录历史方案/重复文档**：本批**不做**移动归档（跨 repo-boundaries/CLAUDE/repo-map 引用更新风险大于收益），记入 C215-1 移交后续文档批次。

## 抽检通过
- ✅ `frontend/src/pages/testcase/index.tsx:45,376` — Playground Tab 下架后无组件 import，页面删除后 `npm run typecheck` 绿
- ✅ `frontend/src/router/index.tsx:245-246` — /testplan 重定向 /testcase，删除页面无残留
- ✅ `backend/app/services/menu_service.py:22` — `menu:special`/`menu:perftest` 仅在 `HIDDEN_MENU_CODES`；`test_menu_visibility_flags` 4/4 绿
- ✅ `COMMANDS.md` §5 — V1 工具退役标注与 `test-platform/tools/` 不存在一致
- ✅ 全量回归：前端 vitest 129/608 绿；后端 pytest 2362 passed/1 baseline fail（batch-212 同基线）
- ✅ `audit-ai-pr.ps1`（基础审计 + 成功检查）待 PR 后执行

## 判决
**APPROVED** —— 允许进入合入流程。先创建 Draft PR，待 required checks 全绿 + `audit-ai-pr.ps1 -RequireSuccessfulChecks` 通过后 squash 合并到 main（用户已提前授权推送+PR+合入）。

## 下一批次 Leader 条件
- C215-1: 根目录历史方案/重复文档归档 —— 将 `测试平台-前后端分离重构方案.md`/`CamelTv-测试自动化平台-建设方案.md`/`知识库.md`/`知识中心-用户使用手册.md`/`test-测试平台设计方案.md` 移入 `docs/archive/` 并同步 `repo-boundaries.json`/`CLAUDE.md`/`docs/repo-map.md`/`docs/document-standards.md` 引用；解除条件=文档重构批次完成 + 全仓 rg 无断链。

## 流程回写（Batch 75 起强制）
| 发现 | 处理 | 落点 |
|------|------|------|
| 删除组件时发现其依赖（SphereTab importing toggle/toggle-group）未在首轮清单中；需先梳理交叉依赖再删 | 执行时补充删除依赖项 + 同步 guard test / eslint-suppressions | work-logs/batch-215-dead-code-cleanup-qa-report.md §C3 |
| eslint-suppressions.json 对已删除文件有悬空 key，lint 可能失败 | 删除项同步清理其 suppression key | `test-platform-v2/frontend/eslint-suppressions.json` |
| 根历史文档归档涉及 repo-boundaries.json 等跨文件引用，批量迁移风险高 | 记 C215-1 移交文档批次，不混入死代码批 | `C-CONDITIONS.md` C215-1 |
| dev-gate G0 报送 requirement_service.py except:pass 为存量基线（batch-212 已标注随 batch-215 处理）；但改后端逻辑收益小于风险 | 保留为已知基线不修，记录于 QA | batch-215 qa-report §门禁 |

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| ~4h / ~5h | 0/0/0/2 | 2 | 引用耦合 / 文档迁移 | 删除组件前先查交叉依赖（含 suppression、guard test 清单）；文档归档拆分独立批次 |

**技能使用**: `cameltv-agent-team`（六部门）、`cameltv-bug-guard`、`cameltv-ui-conventions`、`cameltv-doc-check`、`audit-ai-pr`
