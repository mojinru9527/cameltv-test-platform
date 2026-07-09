# 🗂️ Dev 部门项目看板 — Batch 15 · M5/M6 持续学习闭环

> **上一批次**：[batch-14 (M4 Agent 编排)](DEV-batch-14-rag-m4-agent-orchestration.md) — ⏳ 待启动
> **M5/M6 定位**：让知识库"活"起来——需求变更自动触发 Agent，跨迭代沉淀知识包，实现测试智能体的持续进化

## 项目信息

| 字段 | 值 |
|------|-----|
| **里程碑** | M5（自动触发）+ M6（迭代知识包沉淀） |
| **关联** | batch-11「后续里程碑」M5/M6 定义 + [ADR-0009](../../docs/adr/0009-knowledge-center-agent-continuous-learning.md) |
| **状态** | 🔄 进行中（M5 变更检测+自动触发已落地；M6 迭代知识包待后续） |
| **前置依赖** | M0–M4 全部完成；Agent 编排引擎稳定运行；至少一个迭代周期的知识积累 |

## ℹ️ 里程碑拆分

| 子里程碑 | 目标 | 核心问题 |
|----------|------|----------|
| **M5** 自动触发 | 需求文档/Swagger 更新 → 自动启动 Agent 分析 → 产物入审核队列 | "什么时候该跑 Agent？" |
| **M6** 迭代知识包 | 按迭代/版本归档知识快照 → 跨迭代对比 → 趋势洞察 → 回归范围预测 | "这个迭代学到了什么？" |

## ℹ️ 架构决策（草案，待 M5/M6 启动时 ADR 正式化）

| # | 决策 | 方案 |
|---|------|------|
| D1 | 触发检测 | 内容哈希变更检测（`content_hash` 对比）优于时间戳；支持手动触发覆盖 |
| D2 | 触发策略 | 可配置规则：on_requirement_update / on_api_change / on_defect_spike / manual_only |
| D3 | 知识包存储 | `knowledge_iteration_package` 新表：迭代快照（entity snapshot + relation snapshot + stats） |
| D4 | 跨迭代分析 | SQL 聚合查询（同项目跨 iteration 对比），不引入时序数据库 |
| D5 | 队列管理 | M5 引入 Agent 任务队列（内存队列 + DB 持久化，初版不依赖 Redis/Celery） |

## 🎯 交付切片

### M5 Slice 1 — 变更检测 + 自动触发引擎

- [ ] **变更检测服务** `services/knowledge/change_detector.py`（新）：
  - `detect_changes(project_id) → list[ChangeEvent]`：对比 source 当前 content_hash 与上次入库记录
  - ChangeEvent 类型：`requirement_updated` / `api_schema_changed` / `new_defect` / `execution_failure_spike`
  - 变更范围计算：哪些 API/模块受影响（利用 M3 知识图谱 `contains` 关系）
- [ ] **触发策略配置**（`knowledge_trigger_rules` 表或 JSON 配置）：
  - 项目级开关：`auto_trigger_enabled`（默认 OFF）
  - 规则模板：`{event_type, agent_type, auto_approve_threshold?}`
  - 例：`on: requirement_updated → run: impact_analysis, case_generation`
  - 防抖：同一 source 5 分钟内不重复触发
- [ ] **触发调度器** `services/knowledge/trigger_scheduler.py`（新）：
  - 入口：可被 API 手动调用 / Jenkins webhook / cron 定时扫描
  - 读取触发规则 → 匹配 ChangeEvent → 入 Agent 任务队列 → 调 M4 编排器
  - BackgroundTasks 执行，不阻塞触发源
- [ ] **触发 API**：
  - `POST /agents/triggers/check`：手动执行变更检测（返回检测到的变更列表）
  - `GET /agents/triggers/rules`：查看当前触发规则
  - `PUT /agents/triggers/rules`：更新触发规则（`agent:admin`）
- [ ] **C1 验收**：更新需求文档 → 哈希变更被检测 → Agent 自动启动 → 产物入审核队列

### M5 Slice 2 — Agent 任务队列 + 并发治理

- [ ] **Agent 任务队列** `services/knowledge/agent_queue.py`（新）：
  - 内存队列（`asyncio.Queue`）+ DB 持久化（`agent_queue_item` 表）
  - 并发控制：每个项目最多 2 个 Agent 并发执行
  - 优先级：手动触发 > 自动触发
  - 重试：失败任务自动重试 1 次（间隔 30s）
- [ ] **队列前端**（Agent 工作台扩展）：
  - 「任务队列」Tab：pending/running/completed/failed 四列看板
  - 队列项卡片：agent_type + trigger_source + created_at + status
  - 手动取消 pending 任务
- [ ] **C2 验收**：连续触发 5 个 Agent → 队列排队执行 → 最多 2 并发 → pending 可取消

### M6 Slice 3 — 迭代知识包

- [ ] **迭代模型** `models/knowledge.py` 追加：
  - `KnowledgeIteration` 表：`id, project_id, iteration_name, version, start_date, end_date, status, metadata_json`
  - `KnowledgeSnapshot` 表：`id, iteration_id, snapshot_type (entity/relation/chunk/stats), data_json, created_at`
- [ ] **迭代管理 API**：
  - `POST /knowledge/iterations`：创建迭代
  - `PUT /knowledge/iterations/{id}/close`：关闭迭代 → 自动创建快照
  - `GET /knowledge/iterations`：迭代列表
  - `GET /knowledge/iterations/{id}/snapshots`：迭代快照列表
  - `GET /knowledge/iterations/{id}/compare?base_iteration_id=X`：跨迭代对比
- [ ] **快照服务** `services/knowledge/snapshot_service.py`（新）：
  - `create_snapshot(iteration_id)`：捕获当前 project 的 entity/relation/chunk 计数 + 统计摘要
  - `compare_iterations(base_id, target_id)`：对比两个迭代的 entity 增量 / relation 增量 / 缺陷密度变化
- [ ] **C3 验收**：创建迭代 → 关闭 → 快照生成 → 跨迭代对比返回增量数据

### M6 Slice 4 — 跨迭代洞察 + 回归预测

- [ ] **趋势仪表板**（知识中心 Overview 或新 Tab）：
  - 缺陷密度趋势：每个迭代的 defect/API 比值变化
  - 用例覆盖率趋势：test_case/API 比值变化
  - 知识增长率：entity + relation + chunk 总量趋势
  - 图表：`recharts` 折线图/柱状图（项目已有依赖）
- [ ] **回归范围预测** `services/knowledge/regression_predictor.py`（新）：
  - 输入：变更的 API paths / modules
  - 逻辑：查询历史迭代中同一 API 关联的 defect → 计算缺陷复发概率 → 排序
  - 输出：`[{api_path, risk_score, historical_defects, suggested_test_cases}]`
  - 复用 M3 图谱 `affects` 关系 + M2 向量相似度（变更 API 与历史缺陷 API 的 embedding 距离）
- [ ] **预测 API**：
  - `POST /knowledge/predict/regression-scope` → 返回风险排序列表
  - 在接口详情「相关知识」面板中增加「风险评估」区块
- [ ] **C4 验收**：趋势图正确展示跨迭代数据；回归预测对已知高风险 API 打高分数

### M5/M6 Slice 5 — 测试 + 文档 + 全链路验收

- [ ] `tests/test_continuous_learning.py`（新）：
  - `TestChangeDetector`：哈希变更检测、防抖、规则匹配
  - `TestAgentQueue`：入队/出队/并发限制/重试/取消
  - `TestSnapshotService`：快照创建/幂等/跨迭代对比
  - `TestRegressionPredictor`：风险评分排序、边界（无历史数据时降级）
  - `TestTriggerE2E`：需求更新→自动触发→Agent 执行→产物审核（mock LLM）
- [ ] ADR-0012：持续学习闭环架构决策记录（D1-D5 正式化）
- [ ] 全链路验收脚本：手动模拟一个完整迭代周期
  1. 创建迭代 → 导入需求+Swagger → 手动触发 Agent → 审核产物
  2. 更新需求（变更检测触发自动 Agent）→ 新产物对比
  3. 关闭迭代 → 生成快照 → 跨迭代对比
  4. 输入变更 API → 查看回归预测
- [ ] **C5 验收**：`pytest tests/test_continuous_learning.py` 全绿；ADR-0012 accepted；全链路验收通过

## 范围边界（M5/M6 不做）

- ❌ 实时流式 Agent 输出（WebSocket 推送 token 级进度）→ M5 仅轮询，后续迭代
- ❌ 分布式任务队列（Celery/Redis）→ 初版内存队列 + DB 持久化，够用
- ❌ 跨项目知识迁移 → 项目维度隔离，共享学习模式留后续 PRD
- ❌ 自动修复（Agent 直接修改用例/代码）→ 始终人类审核 gate，不做自主变更
- ❌ 知识图谱时序版本（entity 变更历史）→ 仅快照粒度（迭代级），不追踪单 entity 变更

## 风险

| 风险 | 缓解 |
|------|------|
| 自动触发过频繁（噪声） | 防抖（5min）+ content_hash 去重 + 默认 OFF + 可配置规则 |
| Agent 队列堆积 | 并发限制 + pending 可取消 + 监控队列深度告警 |
| 快照数据膨胀（每迭代全量捕获） | 快照仅存统计摘要 + entity/relation 计数，不存全量数据 |
| 回归预测误报（false positive） | 标注置信度 + 降级到纯历史频次（不用向量相似度） |
| 跨迭代对比语义偏移（entity 名称变化） | `entity_key` 稳定唯一键保证可比性 |

## 参考

- [ADR-0009](../../docs/adr/0009-knowledge-center-agent-continuous-learning.md)
- batch-11「后续里程碑」M5/M6 原始定义

## 落地记录（batch-15 · feature/knowledge-m5-m6-continuous-learning）

| Slice | 提交 | 验收 |
|---|---|---|---|
| M5 S1 变更检测+自动触发 | 本批次 | ✅ change_detector + _post_ingest_hooks 统一入口 + /triggers/check API |
| M5 S2 Agent 任务队列 | 待后续 | — |
| M6 S3 迭代知识包 | 待后续 | — |
| M6 S4 跨迭代洞察+回归预测 | 待后续 | — |
| M5/M6 S5 测试+文档 | 待后续 | — |
