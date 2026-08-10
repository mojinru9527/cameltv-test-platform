# Batch 132 — 直属用例可查看/编辑 + 知识图谱计数/分域 QA 报告
> **QA (🔍)** | Date: 2026-08-10 | Verdict: PASS（发布建议 READY）

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 9（PRD 验收标准） | 9 | 0 | 0 |

## 可执行门禁（命令 / 退出码 / 摘要）
| 门禁 | 命令 | 退出码 | 结果 |
|------|------|:---:|------|
| 后端 F821 | `ruff check app --select F821` | 0 | All checks passed |
| 后端导入 | `python -c "from app.main import app"` | 0 | import ok |
| 后端定向 | `pytest test_testcase.py test_knowledge*.py` | 0 | 143 passed |
| 后端全量 | `pytest -q` | 1 | **1297 passed / 3 failed / 3 skipped**；3 失败均为 lanhu-mcp 子模块未初始化的环境基线（`lanhu_mcp_server.py` 不存在），CI 全新检出会初始化子模块，应通过；与本批改动无关 |
| 前端类型检查 | `npm run typecheck` | 0 | tsc -b 通过 |
| 前端构建 | `npm run build` | 0 | built in 8.02s |
| 前端全量 | `npm test` | 0 | **109 文件 / 442 用例全过（基线 440 + 新增 2）** |
| 常见 Bug 扫描 | `scan-common-bugs.ps1` | 2 | HARD=0，WARN=255（仓库基线，无新增 HARD） |
| C 条件审计 | `audit-cconditions.ps1 -RequireLatestBatch` | 0 | hard errors=0, warnings=0（已修 C-CONDITIONS 保鲜漂移） |
| 浏览器验收 | Playwright（API mock，1440×900） | 0 | `browser-acceptance.json` status=pass |
| 截图核验 | vision（qwen-vl） | 0 | 直属行可点击/列表显示/图例"已入库/全量"确认 |

CI 分层：本批变更覆盖 `test-platform-v2/frontend/**` + `test-platform-v2/backend/**` → 双端全量；工作日志/C-CONDITIONS 属 docs 分类。

## 逐条件验证（PRD §2/§4）
| 验收标准 | 结果 | 证据 |
|----------|:---:|------|
| 直属用例可查看/编辑：点击"直属用例 (N)"精确返回直属用例列表，可查看/编辑 | ✅ PASS | 浏览器：直属行是可点击按钮（带箭头），点击触发 `taxonomy_direct=true&taxonomy_domain=FAQ帮助` 请求（列表请求 3→4），列表显示 2 条直属用例；点击"编辑用例"打开抽屉；后端 4 条直属过滤测试（域级/模块级精确、父级含后代不回归） |
| 直属用例为 0 时不显示核算行 | ✅ PASS | countDirectCases 兜底 + 前端仅 direct>0 插入（Batch 131 沿用，未改动） |
| 图谱用例计数与用例库一致（全量入图 + 已入库/全量口径） | ✅ PASS | 后端 sync 服务全量用例入图（幂等，4 测试）；stats 返回 `test_case_total`（用例库权威口径）；浏览器图例"526/7559 已入库"（项目）/ "0/7559 已入库"（平台） |
| 能关联的用例关联对应模块 | ✅ PASS | sync 复用 test_case_linker 建立 tested_by（策略幂等）；C125-3 生产脚本 `sync_all_test_cases_to_graph.py` 就绪 |
| 项目知识/平台研发分域隔离 | ✅ PASS | 后端 graph/view、entities、stats 统一 `_knowledge_domain_filter`（platform 仅来源=platform；孤儿默认归项目域）；单测 `test_graph_view_domains_are_disjoint` 通过；浏览器平台视图请求带 platform 域 |
| 实体列表/统计支持分域 | ✅ PASS | EntityTab 增加"全部域/项目知识/平台研发"筛选（浏览器断言存在）；后端 entities/stats 支持 knowledge_domain |
| 平台域独立知识源接线 | ✅ PASS | classify 支持 knowledge_domain=platform（既有）+ 本批图谱平台域过滤；平台研发 tab 不再混入项目/孤儿数据 |
| 大数据量不崩溃（C126-4 基础） | ✅ PASS | 图例计数改用 stats 权威口径，不再依赖已加载节点子集；7000+ 用例实体渲染按需/聚合由 C126-4 后续深化 |
| 回归无新增失败 | ✅ PASS | 前端 442/442；后端 1297 通过（3 失败为子模块环境基线） |

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 1 | P3 | 后端 3 个 lanhu/deploy 契约测试在本 worktree 因 lanhu-mcp 子模块未初始化失败 | 断言 `lanhu_mcp_server.py is_file` 为 False；非本批代码引起 | 环境基线（CI 会初始化子模块） |

## 发布建议
状态: **READY** · 必修复: 0 · 建议修复: 0（备注：全量用例入图需在生产执行 `sync_all_test_cases_to_graph.py`，衔接 C125-3）

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 8h / 实际 6h | 0/0/0/1 | 0 | 工具链 | 新 worktree 先 npm ci 再跑前端测试；submodule 类基线失败先确认环境再定性 |

**技能使用**: `cameltv-agent-team` → 完整批次六部门；`cameltv-ui-conventions` → 直属行可点击化视觉区分/aria；`cameltv-bug-guard` → 幂等 upsert、无 N+1、既有筛选不回归；`vision` → 截图核验（非测试证据）。
