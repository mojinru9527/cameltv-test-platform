# Batch 132 — 直属用例可查看/编辑 + 知识图谱计数/分域 Leader Verdict
> **Leader (🎯)** | Date: 2026-08-10 | Decision: APPROVED

## 评审摘要
| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | 通过 | taxonomy_direct 直属精确过滤不破坏既有父级含后代语义；全量用例入图幂等 + source 回填；分域过滤孤儿归项目域 |
| 风险 | 中低 | 后端新增过滤参数/同步接口；前端行为改动；无生产用例数据改动 |
| 覆盖 | 通过 | 后端 143 定向 + 1297 全量；前端 442 全量；浏览器证据 + vision 核验 |

## 关键决策（已批准）
1. 直属用例可点击查看/编辑：新增 taxonomy_direct 精确过滤（模块级精确相等/域级空路径），核算行可点击进入列表复用现有查看/编辑链路。
2. 知识图谱全量用例入图 + 计数口径：test_case 实体全量同步并挂"用例库全量"知识源（C125-3/C126-1）；图例/统计用 test_case_total 权威口径。
3. 分域隔离：platform 仅来源=platform；孤儿默认归项目域，两域不再共用数据。

## 抽检通过
- ✅ `test_case_taxonomy.py` direct_only 语义 + `test_testcase.py` 4 条直属过滤测试
- ✅ `test_case_graph_sync.py` 幂等/来源回填 + `test_graph_view_domains_are_disjoint` 分域单测
- ✅ PR #184 checks：AI 交付策略 / 后端 / 前端全量 SUCCESS；`audit-ai-pr.ps1 -RequireSuccessfulChecks` 通过

## 判决
**APPROVED**。一次总确认（2026-08-10）已覆盖推送 + Draft PR + required checks 通过后合入 main；QA 硬门禁全绿、最终审计通过，已转 Ready 并 squash 合入（mergeCommit d951094）。

## 下一批次 Leader 条件
- C133-1：蓝湖证据采集 418 会话失效需识别为会话错误并提供重新登录/更新 Cookie 入口（用户生产复现）。

## 流程回写
| 发现 | 处理 | 落点 |
|------|------|------|
| 直属过滤用"父级含后代"前缀匹配，无直属口径 | 新增 taxonomy_direct 精确过滤 | test_case_taxonomy.py / test_case_service.py |
| 图谱用例计数用加载节点子集冒充总量 | 统计用 test_case_total 权威口径 | schemas/knowledge.py + GraphTab |
| 分域过滤孤儿实体双域重复 | 孤儿归项目域，platform 仅来源=platform | knowledge.py _knowledge_domain_filter |

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 8h / 实际 6h | 0/0/0/1 | 1 | 流程 | 完整批次合入前必须补齐 Leader 判决工件，避免补录 |

**技能使用**: `cameltv-agent-team` → 六部门门禁；`cameltv-ui-conventions` / `cameltv-bug-guard` / `vision` 照常。
