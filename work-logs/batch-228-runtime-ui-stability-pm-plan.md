# Batch 228 — PM Plan

> PM | Date: 2026-09-03 | Mode: full | Executor: Codex

## 规格摘要

**原始需求**：解释并修复生产新业务接入的耐久运行提示、Durable Runtime 无法操作、范围/场景页数据闪烁。  
**目标时间**：单批次完成代码、本地 QA 与 Draft PR 前证据；生产发布另走发布火车。

## 开发任务

### [ ] Task 1：冻结产品与 UI 状态契约（30 分钟）

**描述**：用组件测试固定“基线已就绪但耐久能力未就绪不阻断接入”、Worker 离线可诊断和刷新入口。  
**验收标准**：新测试在实现前失败；文案不要求普通用户执行命令；离线状态不再出现空操作区。  
**涉及文件**：
- `frontend/src/pages/onboarding/__tests__/OnboardingPage.test.tsx`
- `frontend/src/pages/runtime/components/__tests__/WorkerHealthTable.test.tsx`
- `frontend/src/pages/runtime/__tests__/RuntimeAdminPage.test.tsx`

### [ ] Task 2：消除范围/场景重复请求（45 分钟）

**描述**：补页面测试，把刷新触发器从 `loading` 拆成 `reloadVersion`，把 AbortSignal 传到 API。  
**验收标准**：首次挂载每页 1 次 GET；成功操作仅增加 1 次；卸载或依赖变化可取消请求。  
**涉及文件**：
- `frontend/src/pages/missions/__tests__/ScopePage.test.tsx`
- `frontend/src/pages/missions/__tests__/ScenariosPage.test.tsx`
- `frontend/src/pages/missions/scope.tsx`
- `frontend/src/pages/missions/scenarios.tsx`
- `frontend/src/api/scope.ts`
- `frontend/src/api/scenarios.ts`

### [ ] Task 3：修复 Worker 列表契约（40 分钟）

**描述**：先补 registry 回归，再用单次 capability 批量查询组装 Worker 列表和写操作响应。  
**验收标准**：两个 Worker 的能力均正确返回；列表 capability SQL 固定为 1 次，不随 Worker 数量增长。  
**涉及文件**：
- `backend/tests/aitde/v34/test_worker_registry.py`
- `backend/app/modules/aitde/workflow/repository.py`
- `backend/app/modules/aitde/workflow/service.py`
- `frontend/src/api/runtime.ts`

### [ ] Task 4：建立持续心跳生命周期（60 分钟）

**描述**：新增可单测心跳循环，立即发送、按默认 60 秒重复、失败重试；启动脚本同时管理心跳与 Temporal Worker 子进程。  
**验收标准**：瞬时发送失败后继续；停止事件结束循环；脚本退出会清理两个子进程；配置样例与 Runbook 同步。  
**涉及文件**：
- `backend/app/modules/aitde/workflow/worker_heartbeat.py`
- `backend/tests/aitde/v34/test_worker_heartbeat.py`
- `deploy/aitde-runtime/scripts/start-worker.sh`
- `deploy/aitde-runtime/.env.example`
- `deploy/aitde-runtime/README.md`

### [ ] Task 5：补齐 Runtime 管理反馈（45 分钟）

**描述**：增加页面加载错误态、页头刷新和离线恢复说明；保留只有在线 Worker 可排空/禁用的安全边界。  
**验收标准**：加载失败可重试；离线 Worker 能看到原因与刷新动作；能力标签读取列表数据；操作失败有 toast。  
**涉及文件**：
- `frontend/src/pages/runtime/index.tsx`
- `frontend/src/pages/runtime/components/WorkerHealthTable.tsx`
- Task 1 的 Runtime 测试文件

### [ ] Task 6：回归、证据与交付（60 分钟）

**描述**：运行定向与全量检查，启动独立端口本地服务，走查接入、Runtime、范围和场景关键路径并采集三视口证据。  
**验收标准**：Vitest/Pytest 定向、typecheck/lint/build、F821/app import/Alembic、dev-gate、bug scan、C 条件审计均有退出码；浏览器无持续重复 GET、无控制台错误和横向溢出。  
**涉及文件**：
- `work-logs/evidence/batch-228-runtime-ui-stability/README.md`
- `work-logs/batch-228-runtime-ui-stability-qa-report.md`
- `work-logs/batch-228-runtime-ui-stability-leader-verdict.md`
- `work-logs/kanbans/DEV-batch-228-runtime-ui-stability.md`

## 依赖与顺序

Task 1 → Task 2/3/4 → Task 5 → Task 6。预计 4.5 小时。任务 2、3、4 是独立代码切片，但由当前 Codex 单会话依次执行，避免共享 worktree 并发修改。

## 质量要求

- [ ] 每个异步 effect 有 cleanup，所有相关 GET 传 AbortSignal。
- [ ] Worker 列表无 N+1 capability 查询。
- [ ] 心跳间隔默认值严格小于 180 秒离线阈值。
- [ ] 中文状态、暗色主题、桌面/平板/手机无溢出。
- [ ] 不新增密钥默认值，不记录真实 Token。
- [ ] 不以本地测试替代生产部署后验收。
