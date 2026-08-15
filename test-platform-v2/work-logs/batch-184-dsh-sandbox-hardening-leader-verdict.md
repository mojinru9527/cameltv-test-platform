# Batch 184 — Leader 判决：DSH 沙箱安全加固（C172-1/2）

> **mode: full** | 日期：2026-08-16 | 分支：`feature/batch-184-dsh-sandbox-hardening`

## 1. 判决：✅ APPROVED（待用户一次总确认后推送/PR/合入）

## 2. 抽检与复核

| 工件 | 抽检结果 |
|------|---------|
| PRD | mode:full 正确（安全加固+新配置）；C172-1/2 承接明确；非目标合理（OS 级沙箱留部署层） |
| Design | 锁粒度（env+run 整体）、闸门语义（排队不丢任务）、隔离工作区（显式 workspace 也仅作根）与实现一致 |
| Dev | `_concurrency_gate` 默认 1 安全优先；长度配额在 runtime 检查前；python-sdk 恢复逻辑在锁内 finally |
| QA | test_dsh_sandbox 8/8 + test_dsh_tasks 8/8；并发凭据隔离断言直接证明 C172-2 语义 |

## 3. 风险核验

- **并发语义**：python-sdk 串行化是明确取舍（凭据一致性优先），node 路径不受影响；闸门对两运行时统一生效。
- **行为兼容**：工作区由共享改为隔离根——目录层级向下兼容；未改任何公开接口/配置名。
- **生产安全**：DSH_ENABLED 保持 false；启用 checklist 已文档化。

## 4. 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 并发测试需真线程+事件同步 | 顺序调用误判并发（3 次返工） | QA 复盘卡 |
| 安全条件闭环需证据链 | C172-1/2 关闭附 commit + 测试证据 | C-CONDITIONS |
