# Batch 277b-1 — P0-4 `/uitest` 节点化：Leader Verdict

> **部门**：🎯 Leader
> **日期**：2026-11-09
> **输入**：PRD + PM + Design + Dev + QA + 实测证据
> **基线**：`origin/main @ 0fbd420fb`

---

## 1. 判决

# ✅ APPROVED（batch-277b-1，契约与执行器）

**理由**：

- **契约完整**：`ExecutionJob(kind="ui")` + `UiTestRun.execution_job_id` + 载荷 schema + 状态投影，链路可独立单测；
- **零行为变化**：`uitest_execution_mode` 默认 `local`，生产路径、Dockerfile、前端契约全部未动；
- **安全边界正确**：spec 在控制面先过 `spec_guard`，节点只收相对路径并剔除敏感 env；无报告/超时/0 用例一律 `all_pass=false`；
- **投影可靠**：report 后同步 UiTestRun/UiTestJob + 回写用例，失败只记日志不吞节点结果；重复上报幂等；
- **回归干净**：全量 **1332 passed / 43 skipped / 0 failed**、90 条相关回归、12 条新单测、迁移可逆、ratchet increased=0。

**边界（必须明说）**：**P0-4 未闭环**。默认未切 node、控制面 Dockerfile 仍装 Chromium、未跑真实节点 E2E。

---

## 2. M0 状态

```text
✅ P0-5 ai_gateway 清零
🟡 P0-2 DROP 守卫 + downgrade（代码侧完成；演练待运维）
⬜ P0-1 Key 轮换（运维）
⬜ P0-3 磁盘水位（运维）
🟡 P0-4 契约 + 节点执行器（277b-1 完成；277b-2 待真机验收/切默认/去 Chromium）
⬜ TA-001.5 转绿（依赖以上）
→ batch-279（M1）仍不得启动
```

---

## 3. 277b-2 硬约束

| # | 要求 |
|---|------|
| 1 | 测试环境用**真实节点**跑通一次 `/uitest`：`UITEST_EXECUTION_MODE=node`，run 状态 `done`，report.json + 截图 + sha256 证据齐全 |
| 2 | 处理 `xhr_capture_service`（`/ui-tests/capture`）与 playground 的本地 Chromium 依赖（迁节点或显式降级并记录） |
| 3 | 控制面 `Dockerfile` 删除 `playwright install` 两行（node + python），`docker image inspect` 无 Chromium |
| 4 | 默认 `UITEST_EXECUTION_MODE=node` 写入部署配置，并保留 `local` 回滚开关 |
| 5 | 产出 `work-logs/p0-evidence/P0-4-control-plane-no-browser.json`（含命令输出 + 镜像 digest），守卫 P0-4 转绿 |
| 6 | 节点前置自检：`npx playwright --version` 失败时给出可读错误（不要在 node 侧静默 0 用例） |

---

## 4. 技术决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| 是否 per-job 混合 local/node | **否**，平台级开关 | 同一 job 两次触发落到不同执行器会污染状态 |
| 节点如何跑 spec | `npx playwright test`（仓库 tests/playwright 优先，否则证据目录） | 复用现有 spec 资产，不重写用例解释器 |
| 投影失败是否影响上报 | 否，只记日志 | 节点结果优先，平台侧可重放 |
| `execution_jobs.kind` 是否迁移 | 否 | 字符串列，服务常量加 `"ui"` 即可 |

---

## 5. 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| `dev-gate` 的 ratchet 规则比 `ruff check app` 更严（RUF100/UP017） | 提交前直接跑 `quality_ratchet.py` | QA 复盘卡 |
| 在已合并 worktree 继续开发会导致分支元数据失效 | 新批次必须新 worktree；已改文件用 patch + 复制迁移 | 本批执行记录（Dev §偏差） |

---

## 6. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | 1.5-2 人日 / 实际 ≈ 1h |
| 缺陷 | 新增 0 P0；自修 4 处 lint |
| 返工次数 | 2 |
| 根因分类 | 工具链（ratchet 口径） |
| 下次避免 | 提交前跑 ratchet；新批次先建 worktree 再改文件 |

---

## 7. 关联工件

- PRD：[batch-277b-p0-4-uitest-node-prd.md](batch-277b-p0-4-uitest-node-prd.md)
- PM：[batch-277b-p0-4-uitest-node-pm-plan.md](batch-277b-p0-4-uitest-node-pm-plan.md)
- Design：[batch-277b-p0-4-uitest-node-design-spec.md](batch-277b-p0-4-uitest-node-design-spec.md)
- Dev：[batch-277b-p0-4-uitest-node-dev-plan.md](batch-277b-p0-4-uitest-node-dev-plan.md)
- QA：[batch-277b-p0-4-uitest-node-qa-report.md](batch-277b-p0-4-uitest-node-qa-report.md)
- 看板：[kanbans/DEV-batch-277b-p0-4-uitest-node.md](kanbans/DEV-batch-277b-p0-4-uitest-node.md)
