---
title: "CamelTv AIQE — 开发排期 + Dogfood 落地方案"
owner: "qa-team"
created: "2026-11-09"
last_reviewed: "2026-11-09"
status: "proposal"
version: "v1.0"
tags: ["platform-refactor", "ai-agent", "dev-schedule", "dogfood"]
related:
  - "docs/platform-refactor/13-ai-quality-agent-merged-spec.md"
  - "work-logs/batch-274-aiqe-spec-review-leader-verdict.md"
---

# CamelTv AIQE 开发排期 + Dogfood 落地方案

> **面向**：平台开发团队（直接按此执行）+ 项目负责人（每周 Gate 审批）。
> **立场**：13 号规格落地过程中，**AIQE 自己测自己**（dogfood ratchet）——每个里程碑交付的 AI 测试能力立刻用在 AIQE 下一个里程碑的质量保障上。等到 V1 结束，AIQE 已经被自己完整测试一遍，10 条 TC-AIQE 全绿即为对外可用的通关证明。

---

## 1. 核心理念：Dogfood Ratchet（自测棘轮）

传统做法：**先建平台 → 再找项目来试用**。问题：平台建完才发现不好用、不好测自己。

本方案做法：**每个里程碑 M1-M6 新增的 AI 测试能力立刻用来测试刚完成的那一版 AIQE**。

```text
     M1 → 建 Run/Event/Artifact → 用它追踪 M1 自己的开发 Run
     M2 → 建 DAG + Driver       → 用 http driver 回归 M1 的 API
     M3 → 建 A1/A2/A3 Agent     → 用 A1 分析 AIQE 自己的 PRD（13 号）
     M4 → 建 A4 Triage          → 注入真实 bug，让 A4 自己找
     M5 → 建多端 + A5/A6        → 跑 AIQE 前端的 PC/移动矩阵 + 从 AIQE 自己的缺陷学 pattern
     M6 → 全链路 TC-AIQE-001..010 → 10 条验收用 AIQE 跑 AIQE 全绿 = 对外可用
```

**关键**：Dogfood 不是测试阶段最后才做，而是每里程碑**必做**的"过线动作"。过不了 dogfood 的里程碑不能进下一个 M。

---

## 2. 排期总览

### 2.1 时间线（5-6 人团队基准 / 2-3 人团队放大线）

```text
                              5-6 人基准               2-3 人放大
                               │                         │
Week -1 ~ 0   ├─ batch-275 (docs P0 修 13 号)              │
Week 1 ~ 2    ├─ batch-277 (P0 清零) + batch-278 (TA-001)  Week 1 ~ 3
Week 3 ~ 4    ├─ M1 Observable Run                         Week 4 ~ 7
Week 5 ~ 7    ├─ M2 First Mixed Workflow                   Week 8 ~ 13
Week 8 ~ 10   ├─ M3 Agent-Assisted Planning                Week 14 ~ 19
Week 11 ~ 13  ├─ M4 Triage + Regression                    Week 20 ~ 25
Week 14 ~ 17  ├─ M5 Cross-Platform + Learning              Week 26 ~ 32
Week 18 ~ 20  └─ M6 Dogfood Acceptance (TC-AIQE-001..010)  Week 33 ~ 40
              ═════════════════                            ═════════════════
              ≈ 20 周 V1                                   ≈ 40 周 V1
```

### 2.2 人员分配（5-6 人基准）

| 角色 | 全周期投入 | 关键里程碑 |
|------|----------|---------|
| TL / 架构 | 1 × 20 周 | 全程 + Dogfood Gate 审批 |
| 后端 A（Run/Event/DAG） | 1 × 20 周 | M1-M3 主力 |
| 后端 B（Driver/Agent/Triage） | 1 × 20 周 | M2-M4 主力 |
| 前端（Console/Matrix） | 1 × 16 周 | M1/M4/M5 主力 |
| Runner / 自动化（Node/OSS 接入） | 1 × 16 周 | M2/M3/M5 |
| AI / 平台（Agent + eval） | 1 × 16 周 | M3/M4/M6 |
| DevOps / QA（共享） | 0.5 × 20 周 | 全程 CI + Gate |

**总计 ≈ 84 人周 ≈ 420 人日**（含 20% Dogfood 投入）。

### 2.3 批次规划（对接 Agent Team 门禁）

| 批次 | 模式 | 周 | 产出 |
|------|-----|----|------|
| batch-274 | 轻量（本批，已完成） | W-1 | 13 号规格评审 + Leader verdict |
| **batch-275** | 轻量（docs-only） | W-1 | 修 13 号 7 条 P0 → status: active |
| batch-276 | 轻量（docs-only） | W0 | 修 13 号 12 条 P1 |
| **batch-277** | 完整 | W0 ~ W1 | §0 P0-1..5 清零（真实代码/运维） |
| batch-278 | 完整（docs） | W1 ~ W2 | TA-001 代码审计产出 baseline.md ✅（PR #499） |
| **batch-279 ~ 282** | 完整 | W3 ~ W4 | M1 Run/Event/Artifact + M1 Dogfood |
| batch-283 ~ 288 | 完整 | W5 ~ W7 | M2 DAG + Driver + M2 Dogfood |
| batch-289 ~ 294 | 完整 | W8 ~ W10 | M3 Agent + M3 Dogfood |
| batch-295 ~ 299 | 完整 | W11 ~ W13 | M4 Triage + 回归 + M4 Dogfood |
| batch-300 ~ 304 | 完整 | W14 ~ W17 | M5 跨端 + Learning + MCP + M5 Dogfood |
| **batch-305 ~ 307** | 完整 | W18 ~ W20 | M6 TC-AIQE-001..010 全绿 = 对外可用 |

**批次数预估 ≈ 30 批**。沿用 Agent Team 门禁：完整批次六部门工件齐全，轻量批次 PRD-lite + QA + Leader + 看板。

---

## 3. Dogfood Ratchet 详解

### 3.1 棘轮原则

- **每个 M 必须有 Dogfood 产出**，由 QA 部门在该 M 的 QA 报告中单列一节"Dogfood 证据"；
- **Dogfood 必须跑在真实部署的 test 环境**（不是本机 mock）；
- **Dogfood 产出的缺陷直接进 defects 表**，由团队在本 M 内修完，不押后；
- **Dogfood 覆盖率月度递增**：M1 ≈ 10%，M2 ≈ 25%，M3 ≈ 45%，M4 ≈ 65%，M5 ≈ 85%，M6 ≈ 95%+。

### 3.2 棘轮图

```text
┌──────────────────────────────────────────────────────────┐
│ M6 TC-AIQE-001..010 全绿                         ← 外部可用 │
│                                                             │
│ M5 Learning / 跨端矩阵 / MCP                                │
│   └─ Dogfood: 用 A6 挖 AIQE 自己的 bug pattern；跨端矩阵看 │
│      AIQE 前端在 3 viewport + 2 浏览器下的表现             │
│                                                             │
│ M4 Triage + Regression                                     │
│   └─ Dogfood: 故意引入 7 个真实 bug (每类 1 个)，让 A4     │
│      自己归因；缺陷修复后点一键回归闭环                    │
│                                                             │
│ M3 A1/A2/A3 Agent                                           │
│   └─ Dogfood: 让 A1 吃 13 号规格 PRD，自动产出 AC；         │
│      A2 产出 AIQE 的回归用例；A3 自动编排成 Workflow       │
│                                                             │
│ M2 DAG + HTTP/DB Driver                                     │
│   └─ Dogfood: 为 AIQE 后端自己的 /api/v1/aiqe/runs CRUD    │
│      写 DAG 回归套，M2 结束后 AIQE 的 API 由 AIQE 自己回归 │
│                                                             │
│ M1 Run/Event/Artifact 底座                                 │
│   └─ Dogfood: 新表能装下一条真实外部测试 run（即使手工   │
│      导入 Postman 结果），证明"闭环最小环"能通             │
│                                                             │
└──────────────────────────────────────────────────────────┘
```

### 3.3 关键约束

- **Dogfood 不能作弊**：不允许"用脚本模拟 test run 数据塞进 run_events 表"，必须是真实节点真实执行；
- **Dogfood 失败即 M 回退**：某 M 的 Dogfood 失败率 > 20% → 本 M 不过 Gate，加一周修复；
- **Dogfood 证据永久保留**：bundle sha256 + evidence refs 入 `work-logs/dogfood/M{N}/`。

---

## 4. 逐里程碑详细排期

### 4.1 M0：前置阶段（W-1 ~ W2，3 周）

**目标**：13 号规格进入可执行状态 + 现有代码审计清 + P0 阻塞清零。

#### batch-275 — 修 13 号 7 条 P0（W-1，docs-only 轻量，1-2 天）

| 任务 | 修改条目 | 修改位置 |
|-----|---------|---------|
| T275-1 | §4.7 补 version_task_run 对账 | docs/platform-refactor/13-ai-quality-agent-merged-spec.md |
| T275-2 | §4.8 加 execution_job_id 字段 | 同上 |
| T275-3 | §4.14 改为扩 environment | 同上 |
| T275-4 | §4.19 + §0 P0-5 明示 ai_job/ai_shadow_run/ai_gateway_cache 一并删 | 同上 |
| T275-5 | §14 加 TestZeus AGPL 法务硬门禁 | 同上 |
| T275-6 | §4.12 补对象存储选型（候选三选一） | 同上 |
| T275-7 | §21 补 benchmark 数据集来源 | 同上 |
| T275-8 | frontmatter status: proposal → active；version: v1.1-p0-fixed | 同上 |

**DoD**：7 条改动合入；6 部门工件齐；status: active。

#### batch-276 — 修 12 条 P1（W0，docs-only 轻量，2 天）

见 Leader verdict §3。

#### batch-277 — §0 P0 清零（W0 ~ W1，完整批次，3-5 天）

| 任务 | 做什么 | 验收证据 |
|-----|-------|---------|
| T277-1 | 轮换生产 4 个 DeepSeek Key + ai_config 重连 + 真实 LLM 调用一次 | ai_operation_records 新增 status=success 行；curl 200 日志 |
| T277-2 | 备份恢复演练 + DROP 迁移加存在性守卫 + downgrade 可执行 | 备份→恢复→抽行对比；alembic up/down 日志 |
| T277-3 | 磁盘清冷数据 + 盘水位告警确认送达 | 水位 ≤ 80% 维持 48h + 告警平台收条 |
| T277-4 | /uitest 内置浏览器路径从控制面迁至 cameltv-node | 控制面镜像 `docker image inspect` 无 Chromium |
| T277-5 | 删除 ai_gateway/ + ai_job.py + ai_shadow_run.py + ai_gateway_cache.py + 相关 migration | `rg "ai_gateway\|AiJob\|AiShadow"` 命中 0 |

**DoD**：5 条真实证据入 `work-logs/batch-277-aiqe-ta-000-p0-clearance-*`；TA-001.5 CI 守卫脚本写完并通过。

#### batch-278 — TA-001 代码审计（W1 ~ W2，完整 docs-only，5 天）

**产出** `docs/aiqe/baseline.md`，含：

1. **25 张目标表（22 净新建 + 3 扩展）× 现有 43 个模型文件 / 73 张真实表**完整映射（实测口径，见基线 §2/C-10）；
2. 每张表明示：
   - 现有类/字段一览；
   - 目标字段一览；
   - 差异列表；
   - 迁移策略（ALTER 扩字段 / 新表迁移 / 废旧建新 / 兼容层）；
   - 预估迁移脚本行数。
3. **服务层对账**：13 号 §18.5 列的 8 个接入点 vs `app/services/*.py` 实际 **71 顶层 / 123 递归**文件；
4. **路由层对账**：§15 的 **30 个** endpoint vs `app/api/v1/*.py` 实测 **265 paths / 323 operations**；
5. **前端对账**：§18.2 目录 vs `frontend/src/pages/*` 实际页面（19 域 / 153 组件 / 30 路由）；
6. **Driver 现状**：`playwright_executor.py` + `openapi_import_service.py` + `cameltv-node` 真实能力表。

**DoD**：`baseline.md` 产出 ✅（PR #499，`7f205829c`）；用户已确认 D-278-1..3（2026-11-09）；不冲突项打钩 ✅。决策回写 13 号见 `v1.3-baseline-aligned`。

#### M0 Gate

```
✅ 13 号 v1.3-baseline-aligned active
✅ §0 P0-1..5 真实证据入库
✅ docs/aiqe/baseline.md 产出
✅ TA-001.5 CI 守卫启用
```

全绿才进 M1。否则停工修。


### 4.2 M1：Observable Run（W3 ~ W4，2 周）

**目标**：Run/Node/Step/Event/Artifact 底座 + React Run Console MVP + **第 1 次 Dogfood**。

#### 批次拆分

| 批次 | 内容 | 人日 | 并行 |
|------|-----|------|-----|
| batch-279 | TA-005 Run 模型 + 状态机 | 后端 A × 4d | — |
| batch-280 | TA-006 Run Event Collector（Outbox） | 后端 A × 4d | 并 batch-281 |
| batch-281 | TA-007 Artifact Manager | 后端 B × 3d | — |
| batch-282 | TA-008 Run Console MVP | 前端 × 5d | 依赖 279/280 完成 |

#### 每周交付

**W3**：
- Day 1-2：batch-279（TA-005）完成；Alembic 迁移 up/down；状态机单测 ≥ 20 case；
- Day 3-4：batch-280（TA-006）启动；Outbox 事务模式实现；1000 事件 seq 测试；
- Day 5：batch-281（TA-007）启动；对象存储适配（按 batch-275 T275-6 决策）。

**W4**：
- Day 1-3：batch-282（TA-008）；`/runs` + `/runs/:id` + SSE `useRunEvents()`；
- Day 4：集成联调；Run 手工触发 → Event 入库 → 前端实时显示；
- Day 5：**M1 Dogfood**（见下）。

#### 🐕 M1 Dogfood（W4 Day 5）

**目标**：证明 Run/Event/Artifact 闭环可用。

**步骤**：

1. 用现有 Postman 对 AIQE 后端（M1 刚上线的 `/api/v1/aiqe/runs`）发一组真实 CRUD 请求；
2. 手工调用 `POST /api/v1/aiqe/runs` 创建一个"External Manual"类型的 Run，模拟外部测试；
3. 手工 PUT 事件到 `/api/v1/aiqe/runs/:id/events`（10+ 事件：RUN_STARTED / STEP_STARTED × N / ASSERTION_EVALUATED / RUN_FINISHED）；
4. 上传 3 个 Artifact（1 screenshot + 1 log + 1 json response）；
5. 用前端 Run Console 打开该 Run → 时间线 + 证据全部可见 + 可下载；
6. 杀掉浏览器刷新 → SSE 断线重连 + 状态不丢。

**通过标准**：
- Run 的 status × outcome 显示正确；
- Event seq 严格递增无跳号；
- Artifact 的 sha256 校验通过；
- SSE 重连后事件无重复无丢失；
- **本次 Dogfood 自身成为一条"AIQE Run"**（run_key = `RUN-DOGFOOD-M1-001`），永久留存 `work-logs/dogfood/M1/`。

**失败阈值**：任何一项不通过 → M1 不过 Gate，加一周修复。

#### M1 Gate

```
✅ test_runs / node_runs / step_attempts / assertion_results / run_events / run_artifacts 6 张表上线
✅ /api/v1/aiqe/runs CRUD + /events SSE 可用
✅ React Run Console MVP 可访问
✅ M1 Dogfood: RUN-DOGFOOD-M1-001 入库 + 证据包 sha256 通过
✅ 6 部门工件齐
```

---

### 4.3 M2：First Mixed Workflow（W5 ~ W7，3 周）

**目标**：Workflow DAG + HTTP/Playwright/DB-RO Driver + **第 2 次 Dogfood：AIQE 跑 AIQE 的 API 回归**。

#### 批次拆分

| 批次 | 内容 | 人日 | 并行 |
|------|-----|------|-----|
| batch-283 | TA-009 Workflow Schema / Validator | 后端 A × 3d | — |
| batch-284 | TA-010 + TA-010.3 DAG Scheduler + 资源锁 | 后端 A × 5d | 依赖 283 |
| batch-285 | TA-011 RunContext / Variable Store | 后端 A × 3d | 并 286 |
| batch-286 | TA-012 HTTP Driver Adapter | 后端 B × 4d | — |
| batch-287 | TA-013 Playwright Driver Adapter | Runner × 5d | — |
| batch-288 | TA-014 + TA-015 DB Driver + Capability Registry | 后端 B + Runner × 4d | — |

#### 每周交付

**W5**：
- 批次 283/284 → Workflow Validator + DAG Scheduler 基础结构；
- 规划 **M2 Dogfood 用例** 的 Workflow JSON（见下）。

**W6**：
- 批次 285/286 → RunContext + HTTP Driver；
- M2 Dogfood 用例 Workflow JSON 上传并 Validator 过关。

**W7**：
- 批次 287/288 → Playwright Driver + DB Driver + Capability Registry；
- **M2 Dogfood**（见下）。

#### 🐕 M2 Dogfood（W7 Day 4-5）

**目标**：用 AIQE 自己回归 AIQE 自己的后端 API。

**Workflow 示例**（存 `test-platform-v2/tests/aiqe-self/api-dogfood.yaml`）：

```yaml
schema_version: "1.0"
scenario_key: "AIQE-SELF-RUN-CRUD"
contract_version: "v1.1-p0-fixed"
nodes:
  - key: login
    driver: http
    input:
      method: POST
      url: /api/v1/auth/login
      body: { username: "aiqe_bot", password: "${SECRET:aiqe_bot_pwd}" }
    outputs: { token: "$.data.access_token" }
    assertions:
      - { type: http_status, operator: eq, expected: 200 }

  - key: create_run
    driver: http
    depends_on: [login]
    input:
      method: POST
      url: /api/v1/aiqe/runs
      headers: { Authorization: "Bearer ${nodes.login.outputs.token}", Idempotency-Key: "dogfood-m2-${now}" }
      body: { workflow_definition_id: "${FIXTURE:wf_id}", target_environment_id: "...", execution_profile_id: "..." }
    outputs: { run_id: "$.data.run_id" }
    assertions:
      - { type: http_status, operator: eq, expected: 201 }
      - { type: jsonpath, path: "$.data.status", operator: eq, expected: "QUEUED" }

  - key: get_run
    driver: http
    depends_on: [create_run]
    input:
      method: GET
      url: /api/v1/aiqe/runs/${nodes.create_run.outputs.run_id}
    assertions:
      - { type: http_status, operator: eq, expected: 200 }
      - { type: jsonpath, path: "$.data.run_key", operator: regex, expected: "^RUN-\\d{8}-\\d{5}$" }

  - key: verify_db
    driver: db_readonly
    depends_on: [create_run]
    input:
      template: "SELECT status FROM test_runs WHERE id = :run_id"
      params: { run_id: "${nodes.create_run.outputs.run_id}" }
    assertions:
      - { type: db_value_eq, column: "status", expected: "QUEUED" }

  - key: cancel_run
    driver: http
    depends_on: [get_run, verify_db]
    input:
      method: POST
      url: /api/v1/aiqe/runs/${nodes.create_run.outputs.run_id}/cancel
    assertions:
      - { type: http_status, operator: eq, expected: 200 }
      - { type: jsonpath, path: "$.data.status", operator: eventually_eq, expected: "CANCELED", deadline_ms: 10000 }

  - key: verify_cancel
    driver: db_readonly
    depends_on: [cancel_run]
    input:
      template: "SELECT status FROM test_runs WHERE id = :run_id"
      params: { run_id: "${nodes.create_run.outputs.run_id}" }
    assertions:
      - { type: db_value_eq, column: "status", expected: "CANCELED" }
```

**执行步骤**：

1. 把上述 Workflow approve → `workflow_definitions` 一行；
2. `POST /api/v1/aiqe/runs` 用该 Workflow 启动一次 Run；
3. 等 Run 执行完（预计 ≤ 30s）；
4. 检查：所有 6 个 Node 全 PASSED；证据包含 6 份 request/response artifact；DB 验证两次都 PASS；
5. 这个 Run 的 run_key = `RUN-DOGFOOD-M2-001`。

**通过标准**：
- Workflow 执行 outcome = PASS；
- 6 个 Node 全部 PASSED，无 BLOCKED；
- 事件时间线连贯（RUN_STARTED → 6×NODE_STARTED/FINISHED → RUN_FINISHED）；
- HTTP + DB 两种 Driver 全部真实执行有证据；
- **这是第一次 AIQE 跑自己 ——"闭环可用"的硬证据**。

**失败阈值**：任何 Node BLOCKED/ERROR → M2 不过 Gate。

#### M2 Gate

```
✅ workflow_definitions + node_runs + step_attempts 迁移 + 5 Driver 注册
✅ Workflow Validator 拒绝非法 DAG（loop/missing ref/non-idempotent retry）
✅ DAG Scheduler 处理 10 个 Node 并发 + 资源锁 + fencing token
✅ M2 Dogfood: AIQE-SELF-RUN-CRUD workflow 跑 6 Node 全绿
✅ 6 部门工件齐
```


### 4.4 M3：Agent-Assisted Planning（W8 ~ W10，3 周）

**目标**：A0/A1/A2/A3 四 Agent 落地 + benchmark eval + **第 3 次 Dogfood：AI 分析 13 号规格自己产出用例**。

#### 批次拆分

| 批次 | 内容 | 人日 | 并行 |
|------|-----|------|-----|
| batch-289 | TA-019 Agent Service 基座 + A0 Orchestrator + A1 Requirement | AI + 后端 B × 5d | — |
| batch-290 | TA-020 + TA-020.3 A2 Test Design + Oracle 守卫 CI | AI × 5d | 并 291 |
| batch-291 | TA-021 A3 Workflow Planner | AI × 4d | — |
| batch-292 | 收集 benchmark 数据集（30 份需求 + 50 份 PRD） | AI + QA × 3d | 全周期 |
| batch-293 | Agent evals runner + CI 守卫 | AI × 3d | 依赖 289/290/291 |
| batch-294 | 前端 A1/A2/A3 评审 UI（requirement-contracts 页 + 覆盖矩阵页） | 前端 × 4d | — |

#### 每周交付

**W8**：
- batch-292 并行启动（数据集每天收 10 份）；
- batch-289 Agent Service 基座 + A0 + A1 基础；
- A1 对 1 份真实 PRD 跑通 → 产 RequirementContract 草案。

**W9**：
- batch-290 A2 + Oracle 守卫；
- batch-291 A3 + Validator 联调；
- 30 份需求 benchmark 完备。

**W10**：
- batch-293 evals runner + CI 守卫；
- batch-294 前端评审 UI；
- **M3 Dogfood**（见下）。

#### 🐕 M3 Dogfood（W10 Day 4-5）

**目标**：把 **13 号规格书本身** 当作 PRD 喂给 A1 → A2 → A3，产出 AIQE 自己的回归用例集。

**步骤**：

1. **A1 吃 13 号规格 §4 (数据模型) + §5 (状态机) + §15 (API 契约)**：
   - 预期产出：至少 15 条 AC，覆盖 `test_runs 创建`、`状态合法转换`、`WorkflowDefinition 冻结后不可改` 等核心规则；
   - 每条 AC 必须有 source_refs 指回 13 号章节行号；
   - 不允许 hallucinated rule（人审 ≤ 2 条即 PASS）。

2. **A2 产出 TestCase 草案**：
   - 对 15 条 AC 各生成 1-3 个 case；
   - 必须含 steps_json + assertions_json + 24 准则 rule_ref；
   - 每条 case 的 Oracle 层标明（REQ: 13 号 §X.Y 或 STD: 24 准则 A-N）；
   - 人审 ≥ 80% 可执行（即可以直接编排进 workflow）。

3. **A3 自动编排**：
   - 把 A2 产出的 case 绑 Driver（http / db_readonly）；
   - 产出 Workflow JSON，过 Validator；
   - 冻结后 approve；
   - 跑一次 → 全绿 or 列出具体失败原因。

4. **比对**：A3 自动产出的 Workflow **覆盖** M2 Dogfood 手工写的 AIQE-SELF-RUN-CRUD 的所有 Node ≥ 80%（证明 A3 自动化等价手工）。

**通过标准**：
- A1 的 AC source_refs 可追溯率 ≥ 95%；
- A2 的 case 人审可执行率 ≥ 80%；
- A3 产出的 workflow 过 Validator 且跑 outcome = PASS；
- A3 产出的 workflow vs 手工 M2 workflow 的 Node 覆盖 ≥ 80%；
- **run_key = `RUN-DOGFOOD-M3-{A1,A2,A3,E2E}`** 4 条真实 run 入库。

**失败阈值**：A1 可追溯率 < 90% / A2 可执行率 < 70% / A3 产出 workflow 跑失败 → M3 不过 Gate。

#### M3 Gate

```
✅ A0/A1/A2/A3 四 Agent 落地 + agent_executions 审计表
✅ 30/50/20 benchmark 全部达到 §21 指标
✅ Oracle 层守卫 CI 启用（assertion 缺 oracle_layer 拒 PR）
✅ M3 Dogfood: A1→A2→A3 串成一条 AIQE 自产自测链
✅ 前端评审 UI 可用
✅ 6 部门工件齐
```

---

### 4.5 M4：Triage + Regression（W11 ~ W13，3 周）

**目标**：A4 失败归因 + 噪音治理 + 结构化 Defect + 一键回归 + **第 4 次 Dogfood：注入真实 bug 测自己**。

#### 批次拆分

| 批次 | 内容 | 人日 |
|------|-----|------|
| batch-295 | TA-022 Execution Profile + 数据隔离 | 后端 A × 4d |
| batch-296 | TA-023 Interference Detectors（节点 + 控制面） | 后端 B + Runner × 5d |
| batch-297 | TA-024 + TA-024.2 A4 Triage Agent + noise-hint skill | AI × 5d |
| batch-298 | TA-025 Counterfactual Replay Coordinator | 后端 A × 4d |
| batch-299 | TA-026 + TA-027 + TA-027.3 Defect 结构化 + 一键回归 + 噪音规则 | 后端 B + 前端 × 6d |

#### 🐕 M4 Dogfood（W13 Day 3-5）

**目标**：主动注入 7 类真实故障，让 A4 自己归因 + 一键回归修完闭环。

**7 个注入场景**：

| # | 分类 | 注入方式 | A4 应归因到 | 回归闭环 |
|---|------|---------|-----------|---------|
| 1 | ENVIRONMENT | 停 test 环境 Redis 10 分钟 | ENVIRONMENT | 启 Redis → retest PASS |
| 2 | THIRD_PARTY | mock DeepSeek 返回 503 × 3 次 | THIRD_PARTY | 关 mock → retest PASS |
| 3 | TEST_DATA | 用重复 user_id 跑两条并发 run | TEST_DATA / CONCURRENCY | 加 fixture namespace → retest PASS |
| 4 | CROSS_FEATURE | 临时推一个"全局 banner 浮层"feature flag | CROSS_FEATURE_DEFECT | 关 flag → retest PASS |
| 5 | AUTOMATION | kill Playwright 浏览器进程 | AUTOMATION_ERROR | 重启 Worker → retest PASS |
| 6 | TIME | 测试账号的会员到期时间设为 5 秒后 | TIME | 延后到期 → retest PASS |
| 7 | **真实产品 Bug** | 改 `app/aiqe/services/run_state.py::transition()` 偷偷把 `CANCELED → RUNNING` 的 Guard 去掉 | PRODUCT_DEFECT | 修 Guard → retest PASS |

**执行步骤**：

1. 每注入一个场景跑一次 AIQE-SELF-RUN-CRUD workflow；
2. 失败后由 A4 自动生成 TriageCase + 多个 Hypothesis；
3. A4 必须对其中 **第 7 个真实 bug** 归因到 `PRODUCT_DEFECT`（即 A4 找出"状态机被改"这个真 bug）；
4. 7 次失败生成 7 个 Defect Draft（含 steps_to_reproduce + evidence_refs）；
5. 开发修复 → 点一键回归 → 7 次 retest 全部 PASS；
6. 回归 run 与原 run 的对比视图齐全。

**通过标准**：
- 7 个注入场景的归因准确率 ≥ 6/7（≥ 85%）；
- **关键第 7 个真实 bug 必须被识别**（硬门槛）；
- 噪音分类不与 PRODUCT_DEFECT 混淆（即 ENV/THIRD_PARTY/TEST_DATA/CROSS_FEATURE/AUTOMATION/TIME 失败**都不能**被标为 PRODUCT_DEFECT）；
- 对照实验 E1-E6 至少跑过 3 个（如 E2 数据隔离 / E5 Worker 对照）；
- 一键回归 7/7 全绿；
- **run_key = `RUN-DOGFOOD-M4-{01..07}`** + 7 次 regression run。

**失败阈值**：归因准确率 < 85% 或真实 bug 未识别 → M4 不过 Gate。

#### M4 Gate

```
✅ interference_observations + triage_cases + triage_hypotheses + regression_requests 表上线
✅ A4 Triage Agent + noise-hint skill 完成 + 100 标注样本 eval 通过
✅ 11 分类 Detector 节点侧采集就绪
✅ E1-E6 对照实验 Coordinator 可用
✅ Defect 结构化字段 + /defects/:id/regressions API + UI 回归按钮
✅ M4 Dogfood: 7 类故障注入 + 6/7 归因准确 + 7/7 retest PASS
✅ 6 部门工件齐
```


### 4.6 M5：Cross-Platform + Learning + MCP（W14 ~ W17，4 周）

**目标**：跨端矩阵 + A5 Impact + A6 Learning + MCP Gateway + **第 5 次 Dogfood：AIQE 前端跨端跑 + AIQE 从自己缺陷学**。

#### 批次拆分

| 批次 | 内容 | 人日 |
|------|-----|------|
| batch-300 | TA-028 Platform Matrix 前端 + TA-012/013 补 mobile_web driver | 前端 + Runner × 6d |
| batch-301 | TA-029 A5 Change Impact Agent | AI × 5d |
| batch-302 | TA-030 A6 Learning Curator + learning_candidates + bug_patterns | AI × 5d |
| batch-303 | TA-031 VersionTask Quality Gate 接入 | 后端 × 3d |
| batch-304 | TA-032 + TA-032.5 MCP Gateway + Agent Skills 开放标准封装 | 后端 B + AI × 5d |

#### 🐕 M5 Dogfood（W17 Day 4-5）

**目标**：
- **a)** 用 AIQE 的跨端矩阵测试 AIQE 自己的 React 前端在 3 viewport + 2 浏览器下的行为；
- **b)** 让 A6 从 M1-M4 累积的 AIQE 自己的缺陷池里挖 pattern 生成 BugPattern 候选；
- **c)** 用 Codex / Claude Code 通过 MCP Gateway 调 AIQE 的工具（"同一个 skill 包三处可用"）。

**步骤 a**（跨端矩阵）：

| AC | PC Chrome 1920 | PC Chrome 1280 | Mobile Chrome 375 | Mobile Chrome 414 | Safari iOS 390 |
|----|:-------------:|:--------------:|:-----------------:|:-----------------:|:-------------:|
| /runs 列表加载 | PASS | PASS | PASS | PASS | PASS |
| /runs/:id 时间线展开 | PASS | PASS | PASS | PASS | PASS |
| SSE 实时事件流 | PASS | PASS | PASS | PASS | PASS |
| 缺陷对比视图 | PASS | PASS | ? | ? | PASS |

**要求**：每格有独立证据（screenshot + trace）；对 mobile 窄屏不适合的组件（如对比视图）标 `platform_specific_behavior`。

**步骤 b**（Learning Dogfood）：

1. A6 吃 M1-M4 期间积累的 10+ 条 AIQE 自己的 defect（含修复 commit）；
2. 产出 LearningCandidate 至少 3 条（如"outbox 事务模式忘加索引"、"Playwright 清理忘 kill 浏览器"等）；
3. 走 CANDIDATE → EVALUATING → APPROVED 流程；
4. 新 BugPattern 进 benchmark 跑 → 验证"覆盖提升 + 不新增误报"。

**步骤 c**（MCP Dogfood）：

1. 在本机 Codex CLI 执行 `mcp add cameltv-aiqe http://localhost:XXXX`；
2. 让 Codex 调 `mcp://cameltv-aiqe/run.get_summary` 查询 `RUN-DOGFOOD-M3-E2E`；
3. 让 Claude Code 加载同一个 `.claude/skills/exec-web-playwright/` skill 跑一次新 workflow；
4. 两处都能产出合法结果 → **证明 Agent Skills 开放标准**。

**通过标准**：
- 跨端矩阵 PC 全绿 + Mobile ≥ 80% PASS（允许少量 platform_specific）；
- A6 产出至少 3 条 LearningCandidate + 1 条进入 ACTIVE；
- MCP Gateway 可被 Codex + Claude Code 同时调通；
- Agent Skills 跨 3 个 agent（Claude Code / Codex / Cursor）加载同一 skill 跑通；
- **run_key = `RUN-DOGFOOD-M5-{CROSS,LEARN,MCP}`**。

#### M5 Gate

```
✅ TA-028 Platform Matrix UI 可用
✅ A5 Impact Agent + A6 Learning 完成 eval
✅ MCP Gateway + Skills 开放标准封装完成
✅ VersionTask Quality Gate 接入
✅ M5 Dogfood: 跨端矩阵 ≥ 80% + Learning 3 条 + MCP 3 处可用
✅ 6 部门工件齐
```

---

### 4.7 M6：Dogfood Acceptance（W18 ~ W20，3 周）

**目标**：§20 TC-AIQE-001..010 全部由 AIQE 自己跑 + 全绿 = 对外可用。

#### 批次拆分

| 批次 | 内容 | 人日 |
|------|-----|------|
| batch-305 | TA-033 Reliability + Security Hardening（压测 + 杀 Worker + 审计） | DevOps + 后端 × 7d |
| batch-306 | TA-034 + TA-034.2 Sports 纵向验收 + Asset-map 接入 | QA + 后端 + Runner × 8d |
| batch-307 | TA-035 文档 + Ops + Rollback | TL + QA × 3d |

#### 🐕 M6 Dogfood = 终极验收

**TC-AIQE-001..010 全部由 AIQE 自己执行**：

| TC | AIQE 自测法 |
|----|-----------|
| TC-AIQE-001 需求契约冻结 | A1 吃 13 号规格 v1.1 → 冻结 → 编辑一处 PRD → V2 diff → 相关 case 标 needs_review |
| TC-AIQE-002 API→Admin UI→Public API→DB | M5 Dogfood 已跑过的 AIQE-SELF-RUN-CRUD 扩展版，加 UI 层 |
| TC-AIQE-003 首次失败重试不得掩盖 | 用 http driver mock 503 → retry PASS；检查 attempt 1 FAILED 在时间线可见 |
| TC-AIQE-004 跨功能浮层干扰 | 临时推一个 AIQE 自己的 banner feature flag；core_isolated PASS / integration FAIL；A4 归因 CROSS_FEATURE |
| TC-AIQE-005 并发数据污染 | 两个 AIQE Run 同时写同一 defect → 锁 or namespace 保护；A4 归因 TEST_DATA |
| TC-AIQE-006 上游故障 | mock DeepSeek 504；A4 归因 THIRD_PARTY + 不建 AIQE 自身 bug |
| TC-AIQE-007 Runner 故障 | kill Playwright；A4 归因 AUTOMATION；业务断言 NOT_EVALUATED |
| TC-AIQE-008 修复后点击回归 | 故意改坏 AIQE 的 state_transition → 跑 M3 Dogfood workflow 失败 → 转缺陷 → 修 → 点回归 |
| TC-AIQE-009 多端 AC 对照 | 跑 /runs 页在 PC + iPhone + Android 的矩阵 |
| TC-AIQE-010 Learning Curator | A6 从 M6 Dogfood 产生的真实缺陷里产 pattern |

**通过标准**：**10/10 全绿**（允许 TC-AIQE-004 的 integration FAIL 分支，因为那是预期失败）。

**M6 完成 = AIQE V1 对外可用**。

#### M6 Gate = 对外可用门禁

```
✅ 压测：100 并发 Run，Worker 挂 1 个后 Run 不丢；24h 无内存泄漏
✅ Security：RBAC 审计 100% 覆盖；secret 不落日志（扫描 0 命中）
✅ TC-AIQE-001..010 全绿（dogfood run_key 永久留档）
✅ 文档：docs/aiqe/ops.md + rollback.md + onboarding.md 齐全
✅ 新项目接入清单：另一个项目（如 futurewayu）可按 30 分钟清单走通
✅ 6 部门工件齐
✅ C274-x 后续 C 条件全部 Closed
```

**全绿 → 向外发布 "AIQE V1 Available"**。


---

## 5. 周度产出跟踪表

> 每周五由 TL 在 `work-logs/weekly-aiqe-{YYYYww}.md` 落一份简报。

| 周 | 主题 | 完成标志 | Dogfood 产出 | Gate |
|----|------|---------|-------------|------|
| W-1 | batch-274/275 | 13 号 v1.1 active | — | 规格 Gate |
| W0 | batch-276/277 | P0-1..5 清零；CI 守卫启 | — | P0 Gate |
| W1-2 | batch-278 TA-001 | baseline.md 产出 | — | 审计 Gate |
| W3 | TA-005/006 | Run 表 + Event Outbox 可用 | — | — |
| W4 | TA-007/008 | Artifact + Console MVP | **M1 Dogfood**：Postman → AIQE 外部 Run 入库 | **M1 Gate** |
| W5 | TA-009/010 | Validator + Scheduler | — | — |
| W6 | TA-011/012 | RunContext + HTTP Driver | — | — |
| W7 | TA-013/014/015 | Playwright + DB Driver + Registry | **M2 Dogfood**：AIQE-SELF-RUN-CRUD workflow 6 Node 全绿 | **M2 Gate** |
| W8 | TA-019/292 | A0/A1 + benchmark 收集 | — | — |
| W9 | TA-020/021 | A2 + A3 | — | — |
| W10 | TA-293/294 | eval runner + 评审 UI | **M3 Dogfood**：13 号 → A1→A2→A3 自产自测链 4 条 Run | **M3 Gate** |
| W11 | TA-022/023 | Profile + Detectors | — | — |
| W12 | TA-024/025 | A4 + Replay | — | — |
| W13 | TA-026/027 | Defect + 回归 | **M4 Dogfood**：7 故障注入 + 6/7 归因 + 7/7 retest | **M4 Gate** |
| W14 | TA-028 | 跨端矩阵 | — | — |
| W15 | TA-029/030 | A5 + A6 | — | — |
| W16 | TA-031 | Quality Gate 接入 | — | — |
| W17 | TA-032 | MCP Gateway | **M5 Dogfood**：跨端 ≥ 80% + Learning 3 条 + MCP 3 处 | **M5 Gate** |
| W18 | TA-033 | 硬化 + 压测 | — | — |
| W19 | TA-034 | Sports 纵向 | — | — |
| W20 | TA-035 + TC-AIQE | 文档 + 终极验收 | **M6 Dogfood**：TC-AIQE-001..010 10/10 全绿 | **M6 Gate = 对外可用** |

---

## 6. 风险与应对

| 风险 | 概率 | 影响 | 应对 |
|------|:---:|:---:|-----|
| M1 Outbox 事务 seq 竞争 BUG | 中 | 高 | M1 Dogfood 包含 1000 事件 seq 测试 |
| M2 Playwright Driver 与节点权限冲突 | 中 | 中 | TA-001 审计阶段先验证 Node.js runtime 可用性 |
| M3 LLM 成本 / 稳定性波动 | 高 | 中 | P0-1 Key 轮换完成后保留 2 个 provider 做熔断 |
| M3 Benchmark 数据集不足 | **高** | **高** | W8 并行启动数据集收集，不等到 M3 结束 |
| M4 A4 对真实 bug 识别率 < 85% | 中 | 高 | M4 给 1 周 buffer 做 prompt 迭代；若连续 2 轮 < 85% → 把 Learning Curator 从 M5 挪到 M4 辅助 |
| M4 对照实验在生产写数据 | 低 | **很高** | 硬门禁：E1-E6 不允许 target_env.allowed_actions = full_write；代码层检查 |
| M5 MCP Gateway 暴露内网写能力过多 | 低 | 很高 | 只暴露 read，写必须审批；token 白名单 |
| M5 TestZeus AGPL 法务不通过 | 中 | 中 | PoC 失败回退：直接走 Playwright Agents 无 TestZeus |
| M6 TC-AIQE-004 跨功能浮层场景无法复现 | 中 | 中 | 可用 feature flag mock；若真不行允许用静态 fixture 代替 |
| 工期压力导致砍 Dogfood | **高** | **很高** | **硬门禁**：Dogfood 失败 = Gate 不过；这是红线不能让 |
| 人员临时抽离 | 中 | 中 | 关键路径（Run 底座 / A4 / 对照实验）必须有 backup，一人一个 shadow |
| 本地分支 feature/aitde-v39-reality-gate 长期不同步 origin/main | 中 | 中 | batch-277 开工前必须把当前分支的工作并到 main 或归档；AIQE 开发全部从最新 main 开新 worktree |

---

## 7. 2-3 人团队放大线

若实际只有 2-3 人：

| 调整 | 具体做法 |
|------|---------|
| 时间 × 2.0 | 20 周 → 40 周 |
| 并行度 | 每周只做一条主线（后端 or 前端 or AI）；Dogfood 每 M 单独 1 周 |
| 砍能力 | 推迟 V1.1/V1.2：Appium / miniapp / desktop / 硬件 / TesterArmy PoC / Keploy PoC 均延 |
| MVP 定义缩小 | M3 只做 A1 + A2（A3 自动编排延）；M4 只做 A4 规则 + 简版 LLM（E1/E2 两种 Replay）；M5 只做 PC + Mobile Web + A6 基础；M6 验收缩到 TC-AIQE-001/002/004/007/008 五条 |
| Dogfood 不砍 | 哪怕砍能力，每 M 的 Dogfood **一定要跑**，这是防 AITDE 失败模式的护栏 |

**2-3 人 V1 预期**：**40 周（10 个月）交付 MVP+**，V1 完整版延至 V1.1 分期。

---

## 8. 预算（粗估）

### 8.1 人力

| 团队规模 | 工期 | 粗估人日 | 月工资假设 | 粗估总成本 |
|---------|------|---------|----------|----------|
| 5-6 人 | 20 周 | ≈ 420 pd | 2w/pm | ≈ 42w CNY（不含管理/福利） |
| 2-3 人 | 40 周 | ≈ 320 pd | 2w/pm | ≈ 32w CNY |

### 8.2 基础设施

| 项 | 月费 | 20 周总费 |
|----|-----|---------|
| 腾讯云（已有） | — | — |
| 对象存储（Artifact） | ≈ 500 CNY | 2.5k |
| LLM 调用（DeepSeek + 备 provider） | **月 2k-5k** | 10k-25k |
| 开发/test 真机设备（Android + iOS 可选） | ≈ 1k-3k 一次 | 1k-5k |
| **合计** | | **≈ 15k-35k CNY** |

### 8.3 OSS 依赖

- Playwright / Midscene / Appium / Keploy / browser-use / ReportPortal / minium：**全部开源 Apache 2.0 / MIT**，无授权费；
- TestZeus Hercules AGPL-3.0：**除非法务通过，不采**；若采需隔离部署 → 额外 1 核 2G 虚机 ≈ 300 CNY/月。

---

## 9. 对外发布准备

M6 Gate 通过后，发布前准备：

1. `docs/aiqe/onboarding.md`：新项目接入 30 分钟清单；
2. `docs/aiqe/ops.md`：日常运维 / 版本锁 / 升级 / 回滚；
3. `docs/aiqe/user-guide-tester.md`：测试工程师使用手册；
4. `docs/aiqe/user-guide-dev.md`：开发者使用手册；
5. `docs/aiqe/api-reference.md`：REST + MCP 契约；
6. 第二个项目接入（如 futurewayu）作为"异构项目可复用"的硬证据；
7. 版本号：V1.0.0；
8. ADR 终稿：ADR-AIQE-001..010 全部 status: accepted；
9. 关闭所有 C-CONDITIONS 中的 AIQE 相关 C 条件。

---

## 10. 最早可开工时间点与关键依赖

```text
今天                                                      M6 全绿
│                                                          │
▼                                                          ▼
[batch-275 修 P0] → [batch-277 清 P0] → [TA-001 审计] → [W3 ~ W20 真正开发]
      ≈1-2d           ≈3-5d                ≈5d
         │
         └─ 必须先过 "修改后合入" Leader verdict 的 7 条 P0
         
硬依赖：
- 轮换 DeepSeek Key（**用户完成**） → 没有可用 LLM 则 M3+ 全线卡
- 法务对 TestZeus AGPL 的评估（**用户发起**） → 不通过 → PoC 换 Playwright Agents，不影响主路
- 对象存储选型（**用户决定**：腾讯云 COS / MinIO / 本地） → 影响 TA-007
- Benchmark 数据集收集（**平行启动**） → 不启动则 M3 结尾卡

**最早真正开发日**：今天起 **+10-15 个工作日**。
```

---

## 11. 开工判决清单（Final Go/No-Go）

### 开 batch-275 (W-1) 之前，用户需确认：

- [ ] 接受 batch-274 Leader verdict = 修改后合入；
- [ ] 同意按本排期 M1-M6 推进；
- [ ] 同意每 M 的 Dogfood 作为硬门禁（失败即 Gate 不过）；
- [ ] 同意 5-6 人 or 2-3 人团队规模及对应工期；
- [ ] 同意 batch-277 需要用户轮换生产 Key 配合。

### 开 M3 (W8) 之前，必须具备：

- [ ] 至少 30 份真实需求文档（可从历史 batch 的 PRD 收集）；
- [ ] 至少 50 份真实 PRD 评估集；
- [ ] AI Key 稳定可用 ≥ 1 周；
- [ ] M1 + M2 Dogfood 全绿留档。

### 开 M6 (W18) 之前，必须具备：

- [ ] M1-M5 每 M Dogfood 均留档；
- [ ] 真实压测环境（可复用 test env）；
- [ ] 第二个接入项目（futurewayu 或其他）adapter 已写；
- [ ] 文档 ops / rollback / onboarding 草稿完成。

---

## 12. 本方案的 ADR

| ADR | 决策 | 结论 |
|-----|-----|------|
| ADR-AIQE-SCHED-001 | Dogfood 是硬门禁还是软建议？ | **硬门禁**。失败即 Gate 不过。 |
| ADR-AIQE-SCHED-002 | Dogfood 每 M 必做还是只在 M6 做？ | **每 M 必做**。棘轮递增 |
| ADR-AIQE-SCHED-003 | Benchmark 数据集何时开始收？ | **W8 并行启动**，不等 M3 结束 |
| ADR-AIQE-SCHED-004 | TestZeus AGPL 卡住时怎么办？ | **PoC 失败回退**：直接走 Playwright Agents，不影响主路 |
| ADR-AIQE-SCHED-005 | 2-3 人团队时 MVP 定义？ | 砍能力但不砍 Dogfood；MVP 保留 M1/M2/M4/M6 四个 Gate |

---

## 13. 下一步

**本文件产出后 Workflow**：

```text
今天     ├─ 用户阅读本排期（本文件 + 13 号 + batch-274 verdict）
         │
D+1-2    ├─ 用户拍板：接受 or 修订
         │
D+3-5    ├─ 开 batch-275 修 13 号 P0（1-2 天）
         │
D+6-10   ├─ 开 batch-277 清 §0 P0（真实代码/运维，3-5 天）
         │
D+11-15  ├─ 开 batch-278 TA-001 审计（docs，5 天）
         │
D+16+    └─ W3 起真正开发 M1，20 周后 M6 对外可用
```

---

## 14. 附：关联索引

- 评审对象：[13-ai-quality-agent-merged-spec.md](13-ai-quality-agent-merged-spec.md)
- 评审产物：[work-logs/batch-274-aiqe-spec-review-*.md](../../work-logs/)
- 前期落地方案：[12-ai-quality-agent-landing-plan.md](12-ai-quality-agent-landing-plan.md)
- 生产评估：[work-logs/platform-simplification-production-eval-20261007.md](../../work-logs/platform-simplification-production-eval-20261007.md)
- 简化设计：[11-platform-simplification-design.md](11-platform-simplification-design.md)

---

> 本排期是 proposal，进 Agent Team 门禁评审后以 Leader verdict 为准。
> 核心承诺：**20 周 V1 对外可用，每 M Dogfood 全绿留档，防 AITDE 失败模式复发**。

---

## v1.4 执行校准（2026-11-14）

PR #595 后执行包 v1.4 落地为一条独立分支的“执行正确性 + 门禁修复”批次，不新增里程碑：

| 批次 | 内容 | 状态 |
|---|---|---|
| PR-0 | 刷新 `docs/aiqe/baseline.md` 到 `b0f6cdd4c`；核对表/路由/迁移数量 | ✅ |
| PR-1/2 | RunContext Resolver + Assertion Runtime + 结果落库 | ✅ |
| PR-3/4 | HTTP 业务化 + Playwright 真实动作/Trace/证据 | ✅ |
| PR-5/6 | Capability Preflight + Run Launch / Outbox / Reconciler | ✅ |
| PR-7 | Evidence Redactor + Artifact 授权/脱敏 | ✅ |
| PR-8 | Run Console 步骤/Attempt/断言/证据 | ✅ |
| PR-9/10 | Defect Draft 既有 + Regression 真实派发（fixed SHA 校验） | ✅ |
| PR-11/12 | Quality Gate facts-only + Tenant Scope / 生产 Run 默认关闭 | ✅ |
| PR-13–16 | A0–A6 / MCP / 跨端 / Sports pilot 既有能力 | 保持既有批次状态，不因 v1.4 重新宣告生产可用 |

验证命令：

```powershell
cd test-platform-v2/backend
python -m pytest tests -k aiqe -q
python -m pytest -q                       # 全量回归
python -m alembic heads                   # 单 head = 20261124_aiqe_pr595_execution
python scripts/ci/quality_ratchet.py
```

**排期影响**：v1.4 是 M2 执行正确性的收口，不压缩 M2 Gate；M3–M6 的真实 Dogfood 仍按本文件原计划执行。生产 Run 创建保持关闭，PR #595 的 HTTP health smoke 不升级为生产验收。

