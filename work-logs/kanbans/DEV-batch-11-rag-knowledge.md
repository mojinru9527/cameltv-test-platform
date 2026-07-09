# 🗂️ Dev 部门项目看板

> **用途**：追踪「RAG 知识图谱与 Agent 持续学习」M0+M1 落地进度。每次 Dev 部门启动时**必须先读取本看板**。

---

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | RAG 知识图谱与 Agent 持续学习 (M0 治理 + M1 知识源入库) |
| **关联执行文档 (PRD)** | [RAG知识图谱与Agent持续学习能力落地执行文档.md](../../test-platform-v2/docs/RAG知识图谱与Agent持续学习能力落地执行文档.md) |
| **落地方案** | plans/fluffy-humming-flamingo.md（本会话） |
| **总预估工时** | 8h |
| **已用批次** | 1 批 |
| **看板创建** | 2026-07-09 |
| **最后更新** | 2026-07-09 |

---

## 🎯 交付切片进度

> 每个 Slice 经过：📝方案 → 💻编码 → 🔍自测 → ✅审批 → 🚀合入。

| # | Slice | 方案 | 编码 | 自测 | QA | Leader | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:------:|:----:|------|
| 1 | M0 地基：模型+迁移+权限+开关+前端入口 | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ | 6 表建成，只接线 4 张；开关全默认 OFF |
| 2 | M1 知识源/切片入库 + 5 事件 hook | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ | 去重+脱敏+自带 Session；先截断后脱敏 |
| 3 | 审核机制(后端 governance) + 只读前端 + Agent 日志 | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ | 13 路由 + 3 只读 Tab；批量导入受治理门 |
| 4 | 测试与验收收尾 | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ | 22/22 通过；ADR-0009 补齐 |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中
> QA/Leader 已全部通过（详见批次记录 Batch 2/3）。合入 develop 待产品/团队按 [[agent-team-gate]] 拍板。

---

## 📍 当前位置

```
Batch #3 — QA + Leader 两轮评审全部通过，达成「零 P2 未决」的干净 GO，待合入 develop
├── ✅ 后端：6 模型 + 1 迁移(0013) + 6 知识服务 + 2 API 路由(13 端点) + 6 权限点 + 5 开关(全默认 OFF)
├── ✅ 入库 hook：需求/接口导入/接口用例/缺陷/执行失败（自带 Session + BackgroundTasks，先截断后脱敏）
├── ✅ 治理：未审核不得进正式库(403) + 批量导入受 ai_artifact_allow_batch_import 门控 + 生产数据门控
├── ✅ 安全：脱敏加固(JWT/查询串/冒号无引号/单双引号JSON/分隔手机号) + 消除 ReDoS(6900ms→31ms)
├── ✅ 前端：知识中心菜单/路由/入口 + 概览/知识源/AI审核台 3 只读 Tab（tsc 0 error）
├── ✅ 测试：tests/test_knowledge.py 22/22；回归 apitest/swagger 53/53；前端 tsc 双模式 0 error
├── ✅ 文档：ADR-0009 知识子系统架构决策留痕
├── ✅ 评审：QA=NEEDS WORK→(修复)；Leader R1=NO-GO→R2=GO-WITH-FOLLOWUP→R3 收口=干净 GO
└── ⏳ 下一步：产品/团队按 agent-team-gate 拍板合入 develop；唯一 backlog P3-3 随 M4 落地
```

---

## 📜 批次记录

### Batch 1 — M0+M1 全量实现 (2026-07-09)
- **产出**：6 模型 + 迁移 0013 + 6 知识服务 + 13 API 端点 + 6 权限 + 5 开关 + 5 入库 hook + 前端 3 只读 Tab + 13 单测
- **自测**：test_knowledge 13/13 ✅；回归 53/53 ✅；新增前端文件 tsc 0 error ✅
- **耗时**：~4h

### Batch 2 — QA 验收 + Dev 修复 R1 (2026-07-09)
- **QA 结论**：NEEDS WORK（置信度 ~90%）——2 NEW P2（脱敏可绕过 / title·source_ref 未脱敏）+ 3 P3。报告 [QA-batch-11](../reviews/QA-batch-11-rag-knowledge.md)。
- **Dev 修复**：#1 加固 sanitize（JWT/查询串/单引号JSON/分隔手机号）；#2 收口点脱敏 title/source_ref；#3 批量导入唯一受治理入口；#4 补绕过/误伤单测；#5 supersede 旧源。
- **复测**：test_knowledge 13→19/19 ✅；回归 53/53 ✅。QA 复测转 READY(待 Leader)。

### Batch 3 — Leader 终审（两轮）+ Dev 收口 (2026-07-09)
- **Leader R1**：NO-GO(narrow)——发现 QA 漏掉的 NEW P2：`knowledge_ingest_enabled` 默认 True，合入即在共享 test 环境自动激活入库。
- **Dev R2 修复**：blocker→默认 False（5 开关全 OFF）；P3-1 残留脱敏缺口（冒号无引号密钥/JSON 无引号值/点分隔手机号，含中文误伤保护）；P3-2 概览排除 superseded + 级联 chunk；补 ADR-0009。test_knowledge 19→21/21 ✅。
- **Leader R2**：GO-WITH-FOLLOWUP——R1 阻断项+P3-1/P3-2 独立复验真修复；新发现 NEW P2 脱敏 ReDoS（O(n²)，~6.9s/50KB），因入库默认 OFF+后台执行判为「休眠、不阻断合入、放开开关前 must-fix」。报告 [LEADER-batch-11](../reviews/LEADER-batch-11-rag-knowledge.md)。
- **Dev R3 收口**：ReDoS 修复（`_EMAIL_RE` 加量词上界 + 5 处入库改 `sanitize(_truncate(...))`）→ 50KB blob 6900ms→31.4ms；补 ReDoS 回归单测；补 ADR-0009（P3-4）。test_knowledge 21→22/22 ✅；回归 53/53 ✅。
- **结果**：零 P2 未决，达成干净 GO。唯一剩余 P3-3 延后 M4。
- **耗时**：~3h（QA+Leader+两轮修复）

---

## ⚠️ 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| ~~知识入库总开关默认 ON~~ | ~~P2~~ | ✅ 已收口：`knowledge_ingest_enabled` 默认改 False（Leader R1 blocker）。 | Dev | 已解决 |
| ~~脱敏可绕过 / ReDoS~~ | ~~P2×2~~ | ✅ 已收口：加固正则 + 消除 O(n²)（QA #1、Leader R2）。 | Dev | 已解决 |
| 共享测试夹具漂移 | P2 | `conftest.py` 的 `client/auth_headers` 因登录响应体 shape 漂移 + `:memory:` StaticPool 缺失失败，影响既有 API 测试（**非本次引入**）。知识测试已自带独立夹具规避。 | 平台维护者 | 2026-07-09 |

---

## 📋 待跟进 backlog（合入后 / 后续里程碑）

| 项 | 优先级 | 描述 | 归属 |
|----|:------:|------|------|
| P3-3 Agent 读端点权限 | P3 | Agent 运行记录**读**端点现用 `agent:run`（运行动作权限），非查看类。M4 统一设计 `agent:*` 权限族（读/写/管理分离）+ Agent 工作台时一并调整。 | M4 |
| 放开入库开关前核对 | 提示 | 各环境 `.env` 显式设 `knowledge_ingest_enabled=true` 前，确认脱敏对该环境语料充分（脱敏为尽力而为，需随真实语料补强）。 | 运维/平台 |

---

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| 执行文档 (PRD) | [RAG…落地执行文档.md](../../test-platform-v2/docs/RAG知识图谱与Agent持续学习能力落地执行文档.md) | ✅ |
| 落地方案 | plans/fluffy-humming-flamingo.md | ✅ |
| 实现代码 | 各 Slice 文件 | ✅ |
| 单元测试 | test-platform-v2/backend/tests/test_knowledge.py | ✅ 13/13 |
| QA 报告 | 待 QA 部门 | ⏳ |
| Leader Review | 待 Leader | ⏳ |

---

## 📌 后续里程碑（本次不做）

- **M2**：切片向量化（`embedding_id` 填充）+ `/knowledge/search` 混合检索 + 接口详情「相关知识」面板
- **M3**：`knowledge_entity/relation` 建图（Swagger→Service/Module/API/Field）+ 关系浏览页
- **M4**：真正的 Agent 编排（需求理解/影响分析/用例生成）+ 审核台采纳/驳回/批量导入前端写操作
- **M5/M6**：需求更新自动触发 + 迭代知识包沉淀
