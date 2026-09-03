# Batch 228 — Leader Verdict

> Leader | Date: 2026-09-03 | Decision: 有条件通过（待用户总确认、required checks 与最终 PR 审计）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | 通过 | 请求循环、能力契约、常驻心跳和状态反馈均有定向测试 |
| 风险控制 | 通过 | 不从网页远程启动进程；`PROD_RO` 保护不变；不宣称本地等于生产恢复 |
| 覆盖 | 通过 | 后端 2414、前端 622、定向 26、迁移 8、路由守卫 4、12 张截图与 Network 计数 |

## 关键决策

1. B15 同步接入基线与 AITDE 可恢复耐久执行继续使用两套就绪口径；后者未就绪不应阻断前者。
2. Runtime 页面只提供事实、恢复原因和重新检查，不提供无法兑现的远程进程启动按钮。
3. Worker 心跳作为与 Temporal Worker 同生命周期的受管进程，默认 60 秒，严格小于 180 秒离线阈值。
4. Worker 列表直接返回真实 capability，并用一次批量 SQL 避免前端详情 N+1。
5. Scope/Scenario 刷新使用独立版本号，`loading` 只表达 UI 状态，不再承担 effect 触发职责。

## 抽检通过

- `worker_heartbeat.py:43-45/112-145`：心跳间隔约束、失败重试、停止清理。
- `repository.py:70-85` 与 `service.py:71-90`：capability 批量读取和统一响应契约。
- `scope.tsx:48-62`、`scenarios.tsx:54-65`：AbortSignal 与独立 reload 依赖。
- `WorkerHealthTable.tsx:43-67/90-103`：离线原因、真实能力和恢复操作。
- `work-logs/evidence/batch-228-runtime-ui-stability/`：双端全量、门禁、请求次数与三视口证据。

## 判决

本地代码和关键用户路径通过，允许进入 Draft PR 阶段。以下交付门禁未满足前不得合入：

1. 用户明确完成一次总确认，覆盖推送本分支、创建 Draft PR、required checks 全绿后合入 `main`。
2. Draft PR required checks 全绿。
3. `audit-ai-pr.ps1 -RequireSuccessfulChecks` 通过。

满足以上条件后 Leader 才可转最终 APPROVED。生产部署不在本批当前授权范围，生产 Runtime 恢复需另行发布与部署后验收。

## 下一批次 Leader 条件

- 本批不新增重复 C 条件；继续执行 C227-1 的 PR required checks/最终审计门禁。
- C227-2 中真实 AI、业务 OpenAPI/被测环境与生产 Worker/Runner 的解除条件不因本地代码通过而关闭。

## 知识审计

- 新确认的问题模式“单次注册不等于持续在线”已固化到心跳回归、部署 README、PRD 和本判决；“列表缺字段不得由前端 N+1 补齐”已固化到查询数测试。
- 当前会话无知识库写入工具，未执行独立 RAG 入库；仓库内测试与 work-log 作为可追溯事实源。
- 未发现与 `C-CONDITIONS.md`、Batch 227 或现有 Runtime 设计决策冲突。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| Worker 只在启动时注册会在离线阈值后产生假离线 | 增加持续心跳、失败重试与生命周期测试 | `worker_heartbeat.py`、`test_worker_heartbeat.py` |
| Runbook 入口与 Python 包目录未形成可执行契约 | 启动器显式进入 backend，并在启动器测试中固定路径 | `start-worker.sh`、`test_worker_heartbeat.py` |
| 列表漏字段易诱导前端逐行补请求 | 后端一次批量查询并加 SQL 次数断言 | `repository.py`、`test_worker_registry.py` |
| 本批不需要修改 Agent Team 技能模板 | 不改技能，无 CHANGELOG 变更 | 本判决记录 |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 4.5h / 实际约 1.2h | 0/4/2/0 | 2 | 技术债 + 生命周期契约缺口 | Runtime 验收从 Runbook 入口启动，并同时覆盖模块导入、持续心跳时间窗、列表契约与浏览器恢复路径 |

**技能使用**：Agent Team 定义六部门与门禁；Bug Guard 促使清除 2 个异常吞噬硬伤；UI 规范决定离线恢复态；Playwright CLI 提供真实请求和三视口证据。
