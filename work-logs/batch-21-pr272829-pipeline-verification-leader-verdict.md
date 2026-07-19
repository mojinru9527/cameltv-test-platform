# Batch-21 — PR #27/#28/#29 六部门流水线回溯验证 · Leader 终审

> 类型：回溯式流水线验证（Retrospective Pipeline Gate）
> 日期：2026-07-12
> 触发：三条 PR 已合并 develop/master 后，按 `[[agent-team-gate]]` 约定补走六部门流水线验证
> 范围：PR #27（`424cb86` 知识中心 M0–M6 + Agent 工作台 + Wiki 知识库/差异对比，90 文件 +16457/−903）、PR #28（`dd5802a` API/UI 测试真实化 + 失败分析/报告聚合/task_worker，34 文件 +4184/−154）、PR #29（`0404eb2` develop→master 发布合并，无独立内容）

## 终审结论：**Pass-with-notes（通过，附后续优化清单）**

五个部门全部 **Pass-with-notes**，**零 Block、零 P0**。已合并代码通过验证、可运行（QA 实跑 **136 passed / 0 failed / 0 skipped**）、主链路真实闭合、GPLv3 合规、Wiki 能力默认关闭合规、蓝湖回归安全。所有 findings **转为「新分支后续优化」候选**，不回退、不阻断已合并代码。

发布链路可追溯：`git merge-base --is-ancestor origin/develop origin/master` → YES，master(`0404eb2`) 完整包含 develop 与 PR#28。

## 各部门结论摘要

| 部门 | 结论 | 关键 P1（转后续） |
|------|------|------------------|
| 开发 Dev | Pass-with-notes | apitest `create_task` 缺 `BackgroundTasks` 形参 → 每次调用 500（被 task_worker 轮询掩盖） |
| 测试 QA | Pass-with-notes | 三个新服务 failure_analyzer/report_aggregator/task_worker 零单测；真实执行路径仅测 happy-path 辅助函数 |
| 产品 Product | Pass-with-notes | `docs/现状功能PRD.md` 模块 11/12 仍标「演示态/random 模拟」，与 PR#28 真实代码及本文件汇总表自相矛盾 |
| 设计 Design | Pass-with-notes | 无 P1（batch-20 严重级可辨性/深色对比修复已落实） |
| 项目 PM | Pass-with-notes | ①PR#28 未逐切片走流水线（已披露，需补 QA+Leader 归档）；②迁移 `20260710_0017` staging 演练（放开 wiki 开关前硬门） |

## 后续优化清单（新分支办理，按优先级）

### P1（优先）
1. **[Dev] apitest `create_task` 500 修复** — `api/v1/apitest.py:481-527` 补 `background_tasks: BackgroundTasks` 形参（对齐同文件 L245/349/400/667），或删 L522-523 完全依赖 worker。
2. **[QA] 补三个新服务单测** — failure_analyzer（8+ 纯函数分类分支）/report_aggregator（除零/合并统计）/task_worker（信号量并发上限/pending 恢复/线程）；补 api_execution `_do_execute`/`_check_prod_protection`/真实执行分支（httpx MockTransport/respx）。
3. **[Product] `现状功能PRD.md` 诚实性修复** — 模块 11/12 详情段与 §5.2 由「🧪演示态/random」同步为「🟡 真实执行」，删除 random/纯前端旧描述（DEV 方案 M1 验收项）。
4. **[PM] PR#28 补走六部门流水线** — 至少 QA + Leader 终审，产出 qa-report/leader-verdict 归档（本文件为 Leader 侧首份回填）。
5. **[PM] C7 迁移 `20260710_0017` staging 双向演练（upgrade/downgrade）并留痕** — 放开任何 wiki 开关前的生产硬门；当前靠开关默认 OFF 兜底（风险休眠）。

### P2
- [Dev] 双队列重复执行竞态（task_worker 轮询 + BackgroundTasks/线程 消费同一 pending，无原子认领）；建议统一单消费路径或 `UPDATE…WHERE status='pending'` 原子认领。
- [Dev] task_worker 信号量并发上限形同虚设（release 早于线程结束）；改为线程内持有到结束或有界线程池。
- [Dev] api_execution httpx `follow_redirects=True` 对用户可控 URL 无内网/元数据 IP 黑名单 → SSRF 缺口。
- [Dev] wiki 读取面端点（list/get pages·raw-sources·ingest-job·diff-tasks）+ `cancel_ingest_job` 未受 `wiki_enabled` 门禁，与 docstring 不符。
- [Dev] `task.skipped = total - passed - failed + skipped` 取消场景重复计数。
- [Dev] EntityTab 关键字搜索无防抖 + 响应乱序覆盖。
- [QA] diff_classifier 7 种 diff_type 中 `changed`/`ambiguous`/`missing_in_right` 未在 `classify()` 层断言；蓝湖 provider 回归护栏仅断言函数同一性，未锁行为输出。
- [Product] `CLAUDE.md:47-48` apitest/uitest gap 短语滞后（6 项已实现仍标缺失）；UI `/runs/{id}/cancel` 为名义取消（subprocess.run 阻塞、未存 PID、子进程不被杀）。
- [Design] WikiDiffTab 缺「类型/是否已处理」筛选 + 批量确认/忽略/生成产物；`source_refs_json`/`evidence_json` 原始 JSON 平铺；图标按钮缺 aria-label；多处条件类名未走 `cn()`。
- [PM] `tsconfig.tsbuildinfo` 构建缓存被长期跟踪 → `git rm --cached` + `.gitignore`；C6/C8/C14 + Design P2/P3 集中登记进 `docs/改进任务backlog.md`；补/回填 batch-12~15/17 六部门产物；更新陈旧看板状态（batch-15/17 进行中→已交付）；`.claude/tmp/` 加入 `.gitignore`。

### P3
- [Dev] 迁移 `20260710_0016` downgrade 未 drop `ui_test_script` 表；playwright `test_spec` 无路径穿越校验；`playwright_executor._semaphore` 死代码；产物收集 rglob 整目录误归历史产物。
- [QA] diff_classifier docstring `stale` 为死规格（从不产出）；`test_v27_smoke.py` 脚本式非 pytest 用例。
- [Product] diff 维度未覆盖方案 §6.6 的权限角色/数据依赖/版本/证据（`compare_service._DIMENSION_ARTIFACT["版本"]` 死代码）；VNext-N 标号在验收报告与 Wiki 方案间同名不同义易混淆。

## 已确认无问题（护栏有效）
- **GPLv3**：wiki/* 无 GPL/copyright 头、无 nashsu/llm_wiki 源码引用，`diff_classifier` 为自研确定性逐维比对，仅借鉴架构。
- **回归安全**：`extract_features`/`generate_test_cases` 公开行为未变（蓝湖逻辑逐字迁入 `external/lanhu_provider.py`，dict 键/异常语义/默认值一致）。
- **默认关闭合规**：wiki_* 开关默认 False、未开写/触发端点 503；未审产物 `pending` 不进正式资产；差异右侧仅纳入 approved 页。
- **真实执行属实**：apitest 走 httpx、uitest 走 `npx playwright test` subprocess，主链无 random 伪造；apitest/uitest 各三项旧 gap 已补齐。
- **测试真实性**：新增测试均真断言，无 skip/xfail，mock LLM 护栏经验证（source_refs 注入、approved 不覆盖、非 approved 排除均真断言）。
- **shadcn 纯净**：全仓 `src/` 无 antd 引入；导入对话框 §6.1 七态全覆盖。

## 备注
- 本批为已合并代码的回溯验证，findings 依 owner「后续优化另开新分支」约定办理，不在本次收口分支内修复。
- 冗余备份（`stash@{0}` reconcile 快照、`.claude/tmp/wip-main-tree-backup.patch`）在本验证通过后清理。
