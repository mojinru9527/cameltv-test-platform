# CamelTv 测试平台 v2 — 生产级评估报告

> 日期：2026-10-07
> 基线：`origin/main` = `5a36dbf96`（batch-273，2026-10-07 合入）
> 评估人：DeepSeek Harness（direct 任务 `feature/platform-simplification`）
> 证据来源：`docs/platform-refactor/`（01/02/09 定位与白名单）、`work-logs/batch-261~273` 验收/QA 报告、
> `work-logs/batch-269-landing-acceptance-report.md`（九条最终验收）、源码清单（seed/nav/router/config）、
> 生产实测记录（batch-262/269 生产只读复核、batch-272 浏览器渲染证据）。

---

## 0. 一句话结论

平台的**测试管理核心域与 2026-09 刚落地的「版本验收 + 本地执行节点」主链路符合预期**（有真实生产证据：
3 版本演练 50/50 接口 + 29/30 Web、证据包 sha256 校验通过、备份恢复演练、盘水位告警）；
但 **AI 功能域严重偏离预期**——以 AITDE（后端 180 文件 / 22,896 行 + api/v2 27 文件 + 前端 15+ 页）为代表的
AI 工程投入产出失衡：建模链从未产出过真实执行 Run，DSH/Agent/本地 AI 管线等并存的 AI 执行体系上手成本高、
落地效果差，与「平台 = AI 版本验收工作台」的宣称之间隔着**执行链不落地、口径受限、上手成本**三道鸿沟。

## 1. 平台演进时间线（决定本评估口径）

| 时间 | 批次 | 关键变化 |
|------|------|---------|
| 2026-08-13 | batch-165 | 首次功能价值与冗余审计；专项测试/性能监控移除 |
| 2026-09-02 | 02 白名单定稿 | ABCD 分级：AITDE missions 定为 A 级主线（**本次评估用户已反转此决策**） |
| 2026-09 上旬 | batch-212/215/224 | 旧测试计划入口删除+数据只读归档；死代码/V1 CLI 清理；重复模型收敛 |
| 2026-09-18 | batch-255 后 | 定位「控制面 + 本地执行节点」：平台只做登记·调度·证据·知识 |
| 2026-09-18~20 | batch-258~261 | B1-B4 落地：ExecutionJob 协议 + `cameltv-node` 本地节点、执行沙箱 H1、影响图知识主线、体育试点（接口 50 + Web 30） |
| 2026-09-20~23 | batch-262~272 | 生产恢复演练、老队列处置、试点数据集、执行可执行性、冒烟集 45/50、复用埋点、3 版本演练收口、菜单权限对账、按角色导航瘦身 |
| 2026-10-07 | batch-273 | P0-P3 安全与韧性整改（出网守卫/凭据收口/AI 额度闸门/节点韧性/文档口径） |

## 2. 总体判定

| 维度 | 判定 | 依据 |
|------|------|------|
| 测试管理核心（用例/需求/缺陷/接口/UI/环境/定时/发布包） | ✅ 符合预期 | 生产有真实数据与持续使用证据：用例 10,614 条、api 执行 11,704 次、manual 执行 26,240 次、`test_execution` 137,642 行（v40 黑盒 dashboard-stats + batch-269 备份演练抽查）；接口测试+目标环境生产执行审计通过（batch-233） |
| 版本验收主链路（version-tasks + ExecutionJob + 本地节点 + 影响图） | ✅ 符合预期（**业务数据仅试点实例，生产业务数据为 0**） | batch-269 §3 九条验收：8 条达成、⑦ 判定内核达成但复用率非本版自产（C269-1 已登记，batch-270 修复走版本任务流程）；演练控制面为本机试点实例（127.0.0.1:8124 + 试点 SQLite），生产 version_task 0 个（batch-269/270 报告如实记录） |
| 安全与韧性 | ✅ 符合预期 | url_guard 17 例 / spec_guard 20 例 / token 白名单 12 例；生产盘 74%、告警送达确认、备份恢复两次演练一致 |
| **AI 功能域** | ❌ **严重偏离预期** | 见 §3 |
| 0 数据/空置模块（报告/数据集/通知/集成/组织/主题实验室） | ⚠️ 冗余待删 | 生产长期 0 数据；此前审计结论「价值待使用验证」，本次用户拍板删除 |

## 3. AI 功能域专项评估（用户预期 vs 实际）

### 3.1 预期

CLAUDE.md 顶层定位「AI 原生：DeepSeek LLM 驱动用例生成」，建设方案期望「需求 → AI 生成用例 → 执行 → 报告」闭环。
2026-09-02 定位升级为「AI 版本验收工作台：AI 负责用例生成、自动执行、证据整理与知识复用」。

### 3.2 实际（按证据）

| AI 体系 | 代码规模 | 生产落地效果 | 证据 |
|---------|---------|-------------|------|
| 需求文档 → AI 生成用例 | 路由 2 + ai_service | ⚠️ **历史上唯一跑通、当前生产停摆**：曾产出 703 条 AI 用例、99% 采纳率；但 batch-273 取证（2026-10-06）：生产 ai-gateway **12 天零推理请求**（36,502 行日志全是健康检查）、`ai_operation_records` 最后一条 2026-09-07、**4 个 DeepSeek Key 实测全部 401** → 该能力结构完好、配置层失效（重录 Key 可恢复） | platform-feature-value-and-redundancy-audit.md §2.2、batch-273-p0-p3-remediation-report.md §1 |
| AITDE（智能测试任务/场景/契约/执行/验收） | modules/aitde 180 文件 22.9k 行 + api/v2 27 文件 + 前端 missions/executions/campaigns/healing/flaky/production 等 15+ 页 | ❌ **执行链 0 个真实 Run**：AI 链曾是确定性 stub（AITDE-UX-005）；执行 hook 从未注册（activity 只 echo，AITDE-UX-004）；生产无 Worker（AITDE-UX-002）；Run 不提交 Temporal（AITDE-UX-003）；V4.0 黑盒 14/14 路由「未开放」 | v40-ai-blackbox-16.0.0-qa-report.md、v40-production-verify-report.md、改进任务backlog AITDE-UX-001~005 |
| DSH 任务 / Agent 工作台 | services/dsh 12 文件 + agent 队列 + 前端 dsh-tasks 8 文件 | ⚠️ Agent 执行总量 12 次；依赖 DSH 运行时/团队 profile 重基建，上手成本高 | 知识中心概览证据 |
| AI 本地管线（ai-jobs/ai_agent/本地模型/网关） | ai_agent 路由+服务、ai_job 模型、ai-gateway | ⚠️ 批次 235-248 建设的执行/推理管线，生产使用证据薄弱 | 源码清单 |
| 接口用例 AI 生成/泛化 | api_case_generation_service / api_generalization_service | ⚠️ 与「需求→AI生成用例」重复投入；冒烟集为端点选择版（非 AI 产物） | batch-267 口径 |
| 版本任务 AI 方案生成 | version_task_ai_service | ⚠️ 属版本验收主链路的 AI 环节，生产演练中复用建议链路已跑通，但 AI 生成方案环节证据不完整 | batch-269/270 报告 |

### 3.3 偏移根因（三点）

1. **执行链不落地**：AITDE 的「建模」半链（Mission→契约→场景）投入 30+ 批次，但「执行」半链（Worker/驱动/hook/证据）从未在
   生产连通过一个真实 Run——"AI 生成"是 stub、"执行"是 echo，落地效果为 0。
2. **上手成本过高**：环境、驱动、可达性、模型全部需要人工编排（AITDE-UX-001：无经验工程师无法在 5 分钟内从需求走到首次执行）。
3. **多套 AI 体系并存**：AITDE / DSH 团队 / Agent 队列 / 本地 AI 管线 / 版本任务 AI 五套并立，概念重复（02 白名单 D 级已承认），
   维护与理解成本远超单套体系，且互相分流了投入。

## 4. 冗余与空置清单（删除依据）

| 模块 | 生产数据 | 判定 |
|------|---------|------|
| 报告中心 | 0 份报告 | 删除（计划执行聚合出口由版本任务/缺陷承接） |
| 测试数据集 | 0 条（试点数据集除外） | 删除（数据资产收进用例库） |
| 通知配置 | 0 渠道 | 删除 |
| 集成配置 | 0 配置（Jira/TAPD/ELK 从未接入） | 删除 |
| 组织管理 | 0 团队组织 | 删除（项目成员直管） |
| 主题实验室 | 本地设计工具 | 删除 |
| 知识图谱/AI 审核台/平台研发 | 普通用户已隐藏（batch-212） | 删除（知识中心只留项目知识） |
| AITDE 全家 | 0 真实 Run | 删除 |
| DSH/Agent/AI 本地管线 | 12 次 Agent 执行 | 删除 |
| 质量追溯（已并入报告中心 Tab） | — | 随报告中心删除 |

## 5. 风险与债务（简化实施时须处理）

1. **隐藏依赖**：保留模块对删除模块的引用需逐一核实（例：auth/deps 依赖 organization_service 权限链；
   test_plan_service 失败自动链路引用 report/notify；ai_service 引用 dsh harness 降级路径；
   main.py 启动 agent 队列与 v2 路由；models/__init__ 导入删除模型）。
2. **生产库表 DROP 不可逆**：Alembic 迁移须带存在性守卫；生产执行前备份（batch-262 恢复演练已证明备份链路可用）。
3. **登录默认落地**：V4.0 曾把登录后落地改为 `/missions`——AITDE 删除后必须改回工作台/版本验收。
4. **菜单种子与 RBAC 权限点**：menu:missions/menu:runtime/menu:dsh_tasks 等种子与存量权限行需同步清理（batch-271 已建立对账方法）。
5. **导航模型**：MAIN_ROW_DEFS 中「版本验收」组含 menu:missions、「结果与缺陷」组含 menu:report，删除后导航断言（PRIMARY_ENTRY_LIMIT=4）需同步收敛。

## 6. 结论与建议

1. **保留**：测试管理核心 + 版本验收主链路（version-tasks/ExecutionJob/本地节点/影响图/知识库 3 Tab）+ 需求→AI 生成用例 + AI 配置 + 蓝湖证据 + API Token + 定时任务 + 安全守卫（url_guard/spec_guard/ai_guard/沙箱）。
2. **删除**：AITDE 全家、DSH/Agent/AI 本地管线、报告/数据集/通知/集成/组织/主题实验室、知识中心 AI 子能力、open_knowledge/knowledge-mcp。
3. 建议一次性大 PR 完成（用户已确认方案 A），删除清单与实施细节见配套设计文档。
