---
title: "ADR-0009: 知识中心与 Agent 持续学习子系统（治理优先，分阶段落地）"
owner: "tech-lead"
last_reviewed: "2026-07-09"
status: "active"
tags: ["adr", "knowledge", "rag", "agent", "governance"]
related: ["README.md", "0002-sqlite-with-postgresql-upgrade-path.md", "0007-deepseek-llm-test-case-generation.md"]
---

# ADR-0009: 引入知识中心与 Agent 持续学习子系统（治理优先，M0→M6 分阶段）

## 状态

已采纳（M0+M1 已落地；M2-M6 规划中）

## 日期

2026-07-09

## 背景

测试平台已沉淀大量需求、接口、用例、缺陷、执行结果，但这些资产彼此孤立、不可检索、不可复用，AI 生成用例每次都从零开始，缺少历史知识约束。执行文档 [RAG知识图谱与Agent持续学习能力落地执行文档.md](../../test-platform-v2/docs/RAG知识图谱与Agent持续学习能力落地执行文档.md) 规划把平台升级为「需求 → 影响分析 → 用例/数据生成 → 人审 → 执行 → 知识回流」的持续学习闭环。

痛点：
- 领域资产无统一知识表示，无法做 RAG 检索与影响分析
- AI 产物若直接进正式用例库，会污染人工维护的资产、绕过评审
- 生产数据（响应体/token/PII）若无脱敏直接入库，存在数据安全风险

若不做决策：AI 能力停留在「一次性生成」，无法积累；且缺乏治理护栏时贸然接入会带来资产污染与数据泄露风险。

## 决策

引入独立的**知识中心子系统**，遵循「**治理优先、分阶段、默认关闭**」三原则落地：

- **数据模型**：新增 6 张表 `knowledge_source / knowledge_chunk / knowledge_entity / knowledge_relation / ai_artifact / agent_run`。一次性建全 6 表（避免二次迁移），本期（M0+M1）只接线前 4 张的写路径，`knowledge_entity/relation` 留空表给 M3 图谱。
- **非侵入式入库**：领域事件（需求/接口导入/用例/缺陷/执行失败）经 `BackgroundTasks` 在主事务 commit 之后、以**自带 Session** 的独立函数入库，try/except 静默失败——入库永不回滚也不阻塞用户主操作。
- **治理护栏**（M0 核心）：
  - AI 产物（`ai_artifact`）必须 `review_status == "approved"` 才能导入正式用例库，未审核导入抛 403；
  - 全部治理开关**默认 OFF**（`knowledge_ingest_enabled` / `rag_enabled` / `knowledge_graph_enabled` / `ai_artifact_allow_batch_import` / `knowledge_ingest_production_data`），运维评审脱敏与容量后显式开启；
  - 入库前统一**脱敏**（鉴权头/JWT/token/密钥/手机号/邮箱/身份证），生产执行结果额外受 `knowledge_ingest_production_data` 门控。
- **分阶段路线**：M0 治理基座 → M1 知识源入库（无向量化）→ M2 向量化+RAG 检索 → M3 知识图谱 → M4 Agent 编排+审核台写操作 → M5/M6 需求驱动自动化与迭代知识包。
- **RBAC**：新增 `knowledge:view/manage/approve`、`agent:run/admin`、`ai_artifact:import` 权限点；tester 只读。

## 后果

### 正面影响

- ✅ 领域资产统一为可检索、可追溯、可复用的知识底座，为 RAG/图谱/Agent 铺路
- ✅ 治理护栏（人审门 + 脱敏 + 默认关）确保能力可安全渐进启用，不污染正式资产、不泄露敏感数据
- ✅ 入库与主链路解耦，零侵入、零阻塞、失败隔离
- ✅ 一次建全表 + 分阶段接线，避免反复迁移

### 负面影响 / 权衡

- ⚠️ 6 张表 + 后台入库带来存储与写放大成本（故默认关闭，按需开启）
- ⚠️ 脱敏为「尽力而为」正则，宁可多遮蔽，可能对少量正文过度遮蔽；需随真实语料持续补强
- ⚠️ `entity/relation` 空表先行，M3 前为“死表”，需文档标注避免误用
- ⚠️ 后台 `BackgroundTasks` 依赖主 commit 已落库，若未来改为同事务需重新评估一致性

## 弃选方案

### 方案 A: 入库挂在请求主事务内（同 Session）

- 优点：实现简单，强一致
- 缺点：入库失败会回滚用户主操作；大文档解析/切片拖慢响应
- 放弃原因：违反「入库不得影响主链路」，风险不可接受

### 方案 B: 一开始就做向量化 + 图谱（跳过 M0/M1）

- 优点：更快看到 RAG 效果
- 缺点：缺治理护栏即接入生产数据风险高；schema 未沉淀易反复重构
- 放弃原因：治理与数据模型未打牢前追能力，等于在流沙上盖楼

### 方案 C: 引入外部向量库/知识图谱中间件（如 Milvus/Neo4j）

- 优点：功能强
- 缺点：违反 [ADR-0002](0002-sqlite-with-postgresql-upgrade-path.md) 单栈可升级原则，运维复杂度陡增
- 放弃原因：现阶段用 SQLite/PG 内建能力即可覆盖 M1，向量化 M2 再评估轻量方案

## 关联

- 相关 ADR: [ADR-0002](0002-sqlite-with-postgresql-upgrade-path.md)（存储可升级）、[ADR-0007](0007-deepseek-llm-test-case-generation.md)（AI 用例生成）
- 相关文档: [RAG知识图谱与Agent持续学习能力落地执行文档.md](../../test-platform-v2/docs/RAG知识图谱与Agent持续学习能力落地执行文档.md)
- 看板: [DEV-batch-11-rag-knowledge.md](../../work-logs/kanbans/DEV-batch-11-rag-knowledge.md)
- 评审: [QA](../../work-logs/reviews/QA-batch-11-rag-knowledge.md) / [Leader](../../work-logs/reviews/LEADER-batch-11-rag-knowledge.md)
