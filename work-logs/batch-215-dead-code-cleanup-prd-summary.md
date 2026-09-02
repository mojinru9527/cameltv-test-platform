# Batch 215 — Dead Code Cleanup (B5)
> **Product (🟦)** | Date: 2026-09-03 | Status: Draft | Executor: Codex | 完整批次

## 0. 关联
- 上级路线图: `docs/superpowers/plans/2026-09-02-platform-refactor-rollout.md` §0/§2 B5(完整·后端+清理)
- ABC 白名单事实源: `docs/platform-refactor/02-function-abc-whitelist.md` §3 C 级最终清单
- 前置批次: B1(batch-211) 文档落盘、B2(batch-212) 入口收敛、B3(batch-213) 我的待办、B4(batch-214) 傻瓜化组件层
- B5 出口标准（路线图 §2）: `rg 引用审计零遗漏；全量 pytest+typecheck+build 绿；删除项可回滚`

## 1. 问题陈述
平台重构进入 M0 收尾（B1–B5）。经过 B2 入口收敛后，若干 C 级功能已从菜单/路由下架（下线宣称、重定向），但**底层页面/组件/工具与文档仍留在仓库**，形成死代码与陈旧宣称。具体债务：
- `test-platform-v2/frontend/src/pages/testplan/` 独立页已在 batch-212 下架（路由仅 `<Navigate to="/testcase">`），页面文件保留待清理（router/index.tsx:21 注释明确）。
- `test-platform-v2/frontend/src/pages/testcase/playground/index.tsx` Playground Tab 已在 batch-212 下架（`?tab=playground` 回落列表），独立页面保留待清理。
- ABC 白名单 §3：Playground 独立入口、音视频专项 special、性能监控 perftest 的「宣称/入口」已下架，**代码冻结待完成**。
- ABC 白名单 §3：V1 遗留 CLI 工具（11 个，batch-96 已批准废弃）代码已随 batch-98/100 移除，但 `COMMANDS.md`、根目录历史方案文档仍保留陈旧描述。
- ABC 白名单 §3：全仓无引用页面/组件/路由/服务/文档；根目录历史方案/重复文档/`_tmp_*`。
- 根目录存在大量未跟踪 `_tmp_*` 探测/清理脚本（主 checkout 171 个），污染 `git status`，无 `.gitignore` 兜底。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 死页面（testplan/playground 独立页） | 存在 | 删除且无残留引用 | 本批 |
| 全仓代码引用审计 | 有死文件 | 被删除项零残留引用（rg 复核） | 本批 |
| 前端 typecheck/build/vitest | 绿 | 绿（删除后仍全绿） | 本批 |
| 后端 F821/受影响 pytest | 绿 | 绿 | 本批 |
| 根目录 `_tmp_*` 未跟踪污染 | 171 | 清理 + `.gitignore` 兜底 | 本批 |
| special/perftest 代码冻结 | 宣称已下架 | 无专属前端入口/宣称残留 | 本批 |

## 3. 非目标（本次不做 / 豁免）
- **不删除 TestPlan 数据**：只删前端页面，数据只读归档随 batch-224（D 级收敛）。
- **不删除后端 `/api/v1/playground/*` API**：编译能力并入主链路场景执行（ABC §3），后端 API 冻结保留，前端 `src/api/playground.ts` 客户端接口保留供 M1 复用。
- **不删除 testcase/apitest/uitest 三大资产能力**：用户定稿保留。
- **不删除 B4 `components/foolproof/*` 组件**：批量空态教学随后续批次补齐，非死代码。
- **不删除 `components/TriagePanel.tsx`/`knowledge` 维护 Tab 组件/`release-bundles` 组件**等有测试耦合或后续复用意图的组件：本次不列为删除项。
- **不进行 DB 迁移**：本批无 schema 变更。
- **不改部署/CI**：仅代码与文档清理。

## 4. 用户故事 + 验收标准
- As a 平台维护者, I want 删除不再被路由/菜单引用的页面与组件, 清理根目录临时文件, so that 代码量与 `git status` 干净, M0 收尾。
  - 验收：Given B2 已下架 /testplan 与 Playground / When 执行引用审计与全量 build/test / Then 删除项无残留引用且 build/test 全绿。
- As a 维护者, I want 把 V1 工具陈旧文档与 special/perftest 宣称从文档中移除, so that 文档与代码一致。
  - 验收：`rg 'special|perftest'` 在 README/COMMANDS 无「入口/宣称」残留；COMMANDS.md §5 V1 工具段更新。
- As a 维护者, I want 根目录 `_tmp_*` 被 .gitignore 兜底并清理, so that `git status` 干净。
  - 验收：根目录新增忽略规则，`_tmp_*` 不再出现在 `git status`；主 checkout 的临时文件被清理。

## 5. 技术考量
- 前端删除基于 import 图引用审计（entrypoint=main.tsx 可达性），与 rg 全仓复核双重验证。
- 删除项「可回滚」：均在 git 历史中可恢复（`git rm` 保留记录），无需额外快照。
- 后端路由全部经 `app/api/v1/router.py` 显式 include_router，无隐性引用；本批不删后端 API 路由。
- 根目录文档清理采用「归档 + 引用更新」方式，避免破坏 repo-boundaries.json / CLAUDE.md / repo-map.md 交叉引用。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本分支合入 | 平台维护者 | 前端 typecheck/build/vitest + 后端 F821/pytest 全绿 |
| M0 里程碑 | 平台 | B1–B5 合入，死代码已清、C 级入口下架 |

## 7. 技能使用
- `cameltv-agent-team` → 六部门 Pipeline（本 PRD + PM/Design/QA/Leader/看板）
- `cameltv-bug-guard` → 删除前核对 useEffect 清理/路由重定向/权限最小集（本批为纯删除，无新增副作用）
- `cameltv-ui-conventions` → 确认删除不破坏 `@/ui` 语义 UI 系统与 `@/components/ui` 边界
- `cameltv-doc-check` → 文档保鲜核对（COMMANDS.md / README / root 文档）
