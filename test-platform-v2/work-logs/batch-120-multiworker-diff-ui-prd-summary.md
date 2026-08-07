# Batch 120 — PRD Summary（异步多 worker + 采集对接 + 缺口前端 + 外部解锁尝试）

> **Product (🟦)** | Date: 2026-08-07 | Status: Review | **mode: full**
> 判定：含新能力（C117-2 DB 队列多 worker、C119-1 采集对接、C119-2 缺口前端）→ 完整批次。

## 1. 问题陈述

1. **C117-2 多 worker 不可用**：异步 AI 任务走进程内注册表（`ai_tasks.py`），多 uvicorn worker 各自持有注册表，任务只被提交进程消费；请求可能被另一 worker 轮询到空任务。
2. **C119-1 差异面板手动粘贴**：batch-119 ProductionDiffPanel 需手动粘贴生产页面清单，未对接平台采集（`/ui-tests/capture` 已有 314 样本）。
3. **C119-2 缺口提示仅后端**：C114-1 只有 `POST /interaction-coverage/gaps`，前端不可见，测试人员看不到交互覆盖缺口。
4. **外部项设备就绪**：Test5 契约（C74-2/C95-1/C111-4）与 iOS 采集（CP-C2/C84-1/C95-2）用户表示设备已就绪——本批探测实际可达性并登记状态。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| C117-2 多 worker | 进程内注册表 | DB 队列 + 原子认领，多 worker 可消费；单测覆盖认领互斥 | 本批 |
| C119-1 采集对接 | 手动粘贴 | 面板输入采集任务 ID → 加载 pages 生成差异 | 本批 |
| C119-2 缺口前端 | 仅后端 | 需求页/交互页显示覆盖率 + 缺口清单 | 本批 |
| 外部项状态 | Deferred | 探测后更新解除条件（可解锁则推进） | 本批 |

## 3. 非目标（本次不做 + 豁免理由）

- **C106-2 邀请链接观察**：用户明确跳过。
- **外部项若仍不可达**（Test5 网关 503/VPN 未就绪、solox 缺 iOS 26.5 DeviceSupport）：保持 Deferred，更新解除条件与最新探测证据。
- **C99-1 PERF-OPT、C96-1（C27-C1~4）**：大项 Epic，保持 Open。
- **C119-1 不做全量页面级 XHR→页面映射**：本批用采集任务的 pages 字段直接生成清单（URL→label 简易映射）。

## 4. 用户故事 + 验收标准

- **US-1 C117-2**：As a Dev, I want 异步任务跨 worker 可消费 so that 多 worker 部署不丢任务。
  验收：Given 任务提交 / When 任意 worker 轮询 / Then DB 认领（原子 UPDATE status pending→running），结果写回 DB，多 worker 不重复执行；单测覆盖。
- **US-2 C119-1**：As a 测试工程师, I want 差异面板直接加载平台采集结果 so that 无需手动粘贴。
  验收：Given 采集任务 ID / When 面板加载 / Then 从 GET /ui-tests/capture/{id} 取 pages 生成生产清单，vitest 通过。
- **US-3 C119-2**：As a 测试工程师, I want 前端看到交互覆盖缺口 so that 覆盖无遗漏可评估。
  验收：Given 交互拓扑边 + 平台交互用例 / When 打开面板 / Then 显示覆盖率 + 缺口清单，vitest 通过。
- **US-4 外部探测**：As a QA, I want Test5/iOS 状态更新 so that Deferred 条件准确。
  验收：Given 设备/凭据现状 / When 探测 / Then 记录可达性与阻塞点，更新 C-CONDITIONS.md。

## 5. 技术考量

- C117-2：新增 `ai_task` 表（id/type/project_id/status/progress/result_json/error/locked_at/时间戳）+ Alembic 迁移；ai_tasks.py 改为 DB 队列：submit 插 pending，worker 循环原子认领（`UPDATE ... WHERE status='pending'` 且未锁定），完成写回；get_ai_task 读 DB。
- C119-1：`ProductionDiffPanel` 增加「加载采集任务」输入 → `GET /ui-tests/capture/{task_id}` → pages → label 映射（URL 去域名取 path，取最后有意义段）。
- C119-2：新增 `InteractionGapPanel`（需求页），内置模块级代表边清单（取自 batch-113 3172 边证据的常见入口），调 `POST /interaction-coverage/gaps` 渲染覆盖率与缺口。
- 外部探测：Test5 走 VPN 后探 gateway health + konfi/admin 登录端点；iOS 用 tidevice 探测设备 + solox 版本支持核对。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main → Railway 部署 | 全平台 | 门禁全绿；多 worker 部署验证 |
| 部署后复测 | QA | 采集对接/缺口面板可用 |

## 7. 技能使用

- `cameltv-agent-team`：六部门流水线。
- `cameltv-bug-guard`：迁移/队列实现避坑。
- `cameltv-ui-conventions`：两个前端面板。
- `playwright-cli`：外部探测（如需要）。
