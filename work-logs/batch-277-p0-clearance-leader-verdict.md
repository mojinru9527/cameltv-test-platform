# Batch 277a — AIQE §0 P0 代码侧清零：Leader Verdict

> **部门**：🎯 Leader
> **日期**：2026-11-09
> **输入**：PRD + PM + Design + Dev + QA + 实测证据
> **基线**：`origin/main @ 9cf83ee2e`

---

## 1. 判决

# ✅ APPROVED（batch-277a 代码侧）

**理由**：

- **P0-5 完成**：`app/services/ai_gateway/`（8 文件）、3 个 ai_* model、6 个 gateway 端点、10 个配置项、旧 CLI 与 3 个测试全部删除；后端 `app/tests/scripts` 残留 **0**；
- **节点注册表零风险迁移**：`AiAgent` → `ExecutionNode`，表 `ai_agents` 保留——节点注册/派发链路未断（18 条协议测试 + 全量回归通过）；
- **P0-2 代码侧完成**：新迁移 `DROP TABLE IF EXISTS` + downgrade 按原结构重建，`upgrade → downgrade -1 → upgrade` 退出码全 0，表存在性符合预期；
- **TA-001.5 可用**：`check-p0-ready.ps1` 真跑 4/5 未过（正确 fail-closed），`-SelfTest` PASS（绿/红两条路径都验证）；
- **回归干净**：全量后端 **1320 passed / 43 skipped / 0 failed**（188s）；ruff F821 绿；
- 文档同步：ADR-0027/0028/0029 标 superseded、`docs/ai/local-ai-agent.md` 重写、13 号 §0 P0-5 状态回写。

**重要边界**：本批 **不等于 M0 Gate 通过**。P0-1 / P0-3 需生产操作，P0-2 备份演练、P0-4 `/uitest` 剥离仍缺。

---

## 2. M0 状态（14 号 §4.1）

```text
✅ 13 号 v1.3-baseline-aligned active
✅ docs/aiqe/baseline.md（PR #499）
✅ P0-5 ai_gateway 清零（PR 本批）
🟡 P0-2 DROP 守卫 + downgrade（代码侧完成，演练待运维）
⬜ P0-1 Key 轮换 + 真实调用（运维）
⬜ P0-3 磁盘水位（运维）
⬜ P0-4 /uitest 剥离（277b）
⬜ TA-001.5 转绿（依赖以上证据）
→ batch-279（M1）不得启动
```

---

## 3. 对 277b / 运维的硬约束

### 277b（P0-4）

1. `/ui-tests/{id}/trigger` 改为创建 `ExecutionJob(kind="ui")`，由 `cameltv-node`（capability 含 `web`）执行；
2. `UiTestRun` 投影 `ExecutionJob` 状态/结果/证据，**前端 `/ui-tests/runs/{id}` 契约不变**；
3. 控制面 `test-platform-v2/backend/Dockerfile` 删除 `playwright install` 两行（node 与 python），`docker image inspect` 无 Chromium；
4. 完成后写 `work-logs/p0-evidence/P0-4-control-plane-no-browser.json`，`check-p0-ready.ps1` 的 P0-4 必须转绿；
5. 验收必须包含一次真实 `/uitest` 走 node 的 Run（截图 + 证据 sha256）。

### 运维（P0-1/P0-2/3）

1. 轮换 4 把 DeepSeek Key → 真实 `requirement→cases` 调用成功 → `P0-1-ai-key-rotation.json`；
2. 备份 → 恢复 → 抽行对比 → `P0-2-backup-restore.json`；
3. 磁盘 ≤80% 维持 48h + 告警收条 → `P0-3-disk-watermark.json`；
4. 三个 JSON 的 `checked_at` 必须在 30 天内，否则守卫按过期处理。

---

## 4. 本批的技术决策（记录）

| 决策 | 选择 | 理由 |
|------|------|------|
| `ai_agents` 表是否改名 `execution_nodes` | **本批不改**，只改类/文件 | 生产已有节点数据；改名需同步 token/审计引用，收益低 |
| 删除的 gateway 端点是否保留兼容壳 | **不保留** | 仓内无调用方；保留壳会与"删除 ai_gateway"目标矛盾 |
| `api.d.ts` 是否本批重生成 | **不重生成** | 生成文件，无调用方；下次生成自动收敛 |
| 是否修 `test-platform-v2/tests` 的 6 条 stale guard | **不修**（只删无效 token） | main 存量失败、不在 CI；避免扩大范围 |

---

## 5. 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 删除 API 端点会触发 `route_inventory` 基线守卫 | 删端点必须同步 `tests/fixtures/route_inventory.json` 并在 PR 说明 | QA 复盘卡 |
| 批量字符串替换误伤同类名（`AiAgentToken`） | 重命名用 AST 级替换或"先替换完整标识符"校验 | Dev/QA 复盘卡 |
| 规格里"删除 ai_job.py"与"节点注册表"是同一文件 | P0-5 文案需区分"文件/类名"与"表" | 13 号 §0 P0-5 已回写 |

---

## 6. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | 2-3 人日 / 实际 ≈ 1.5h |
| 缺陷 | 新增 0 P0；自修 3 处 |
| 返工次数 | 3（Token 误替换 / heads 解析 / 路由基线） |
| 根因分类 | 工具链（全局替换、正则、基线守卫） |
| 下次避免 | AST 重命名 + 删端点同步 fixture + 守卫脚本先 self-test |

---

## 7. 关联工件

- PRD：[batch-277-p0-clearance-prd.md](batch-277-p0-clearance-prd.md)
- PM：[batch-277-p0-clearance-pm-plan.md](batch-277-p0-clearance-pm-plan.md)
- Design：[batch-277-p0-clearance-design-spec.md](batch-277-p0-clearance-design-spec.md)
- Dev：[batch-277-p0-clearance-dev-plan.md](batch-277-p0-clearance-dev-plan.md)
- QA：[batch-277-p0-clearance-qa-report.md](batch-277-p0-clearance-qa-report.md)
- 看板：[kanbans/DEV-batch-277-p0-clearance.md](kanbans/DEV-batch-277-p0-clearance.md)
- 上游：[13 号 §0](../docs/platform-refactor/13-ai-quality-agent-merged-spec.md)、[baseline C-06/C-07](../docs/aiqe/baseline.md)
