# Batch 277a — AIQE §0 P0 代码侧清零：QA Report

> **部门**：🔍 QA
> **日期**：2026-11-09
> **立场**：默认"需要改进"。本批是**代码批次**（不是 docs-only），按硬门禁执行：全量 pytest + ruff + 结构守卫 + 可逆迁移。
> **基线**：`origin/main @ 9cf83ee2e`

---

## 1. 切片验收

| # | 任务 | 验收 | 证据 |
|---|------|:----:|------|
| 1 | ai_client 直连 | ✅ | 774→484 行；无 `ai_gateway.remote/router/cache/shadow` 调用 |
| 2 | 删 gateway 目录/端点/配置 | ✅ | 8 文件删除；`app.openapi()` 265→**259 paths**；6 端点消失 |
| 3 | AiAgent→ExecutionNode | ✅ | 表 `ai_agents` 未动；`execution_job_service` / `ai_agent_service` 引用替换；18 条协议测试通过 |
| 4 | 迁移可逆 | ✅ | `upgrade head → downgrade -1 → upgrade head` 退出码全 0；表存在性 `[] → [cache, shadow] → []` |
| 5 | 嵌入本地化 + 死代码 | ✅ | `embedding_service` 无 remote；`scripts/ai_agent/` 删除 |
| 6 | TA-001.5 守卫 | ✅ | `-SelfTest` = PASS；真实运行 = FAIL(4/5)，fail-closed 正确 |
| 7 | ADR/文档 | ✅ | 3 个 ADR `status: superseded` + banner；`docs/ai/local-ai-agent.md` 重写；13 号 §0 P0-5 状态回写 |

---

## 2. P0 状态（诚实口径）

| P0 | 状态 | 说明 |
|----|:----:|------|
| P0-1 | ❌ 未完成 | 生产 4 把 Key 轮换 + 真实 LLM 调用，需运维 |
| P0-2 | 🟡 代码侧完成 | DROP 守卫 + downgrade 可执行已交付；备份恢复演练需运维 |
| P0-3 | ❌ 未完成 | 生产磁盘水位，需运维 |
| P0-4 | ❌ 未完成 | `/uitest` 剥离拆 277b；控制面 Dockerfile 仍装 Chromium（守卫按预期报红） |
| P0-5 | ✅ 完成 | 残留 0、单 head、迁移可逆、文档同步 |

**结论：M0 Gate 仍不绿，batch-279 不得开工。**

---

## 3. 硬门禁结果

| 检查 | 命令 | 结果 |
|------|------|:----:|
| 全量后端回归 | `pytest -q`（1320+43） | ✅ **1320 passed / 43 skipped / 0 failed**（188s） |
| 路由基线 | 首次跑出 1 failed（`test_route_inventory`），删除 6 端点后更新 fixture（323→317） | ✅ 修复后通过 |
| ruff F821 | `ruff check app --select F821` | ✅ All checks passed |
| 质量 ratchet（全量 Ruff/mypy） | `python scripts/ci/quality_ratchet.py` | ✅ increased_keys=0（ruff 768→400 / mypy 193→89，删除模块后大幅下降） |
| dev-gate（G0-G2，跳过前端） | `dev-gate.ps1 -SkipFrontend` | ✅ GATE_RESULT=PASS_WITH_WARN（WARN 340 为存量代码） |
| 应用导入 | `from app.main import app` | ✅ 259 paths |
| 残留扫描（app/tests/scripts） | `ai_gateway\|AiJob\|AiShadowRun\|AiGatewayCache` | ✅ **0** |
| 残留扫描（test-platform-v2/tests） | 同上 | ✅ 0（并移除 stale test 中无意义的 token） |
| Alembic 单 head | `scripts/ci/alembic_heads.py` | ✅ 1 head / 119 revisions |
| 守卫 self-test | `check-p0-ready.ps1 -SelfTest` | ✅ PASS（全绿→0 / 缺证据→1） |
| 守卫真实 | `check-p0-ready.ps1` | ✅ FAIL(4/5) —— 正确 fail-closed |
| 前端 | 本批 0 前端改动 | ✅ 由 PR CI 兜底 |

**已知存量债务（未由本批引入）**：`test-platform-v2/tests/test_execution_architecture_guard.py` 在 main 上已有 **6/15 失败**（引用已删除的 `ai_job_dispatch.py` / legacy bridge / `local_agent_mode`），且不在 CI 的 pytest 范围内。本批只删掉其中已无意义的 `ai_gateway` token，未修其余 6 条（避免扩大范围），记入遗留。

---

## 4. 残留与风险

| 项 | 说明 | 承接 |
|----|------|------|
| `api.d.ts` 未重新生成 | 6 个已删端点仍以"类型"存在，无调用方、无运行影响 | 下次生成 API 类型时自动收敛 |
| `ai_agents` 表名未改 | 只改类名/文件名，零数据迁移；表名语义较弱 | 单独迁移批次（需同步 token/审计引用） |
| `/uitest` 仍走控制面 Playwright | P0-4 未做，Dockerfile 仍装 Chromium | **277b** |
| P0-1/2(演练)/3 | 生产操作 | 运维窗口 + `work-logs/p0-evidence/*.json` |
| 6 条 stale architecture tests | main 存量失败、不在 CI | 单独清理批次 |

---

## 5. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | 2-3 人日（代码侧）/ 实际 ≈ 1.5h |
| 缺陷 | 本批新增 0 P0；自修 4 处（`AiAgentToken` 误替换、heads 解析、路由基线 fixture、ai_config 两个 F401 未用导入） |
| 返工次数 | 3 |
| 根因分类 | 工具链（批量同名替换 / 正则解析 revision / 路由基线守卫） |
| 下次避免 | 批量重命名用 AST 级替换而非字符串全局替换；Alembic 解析一律用 AST；删端点必同步 route_inventory fixture |

---

## 6. QA 判定

- P0-5 完成、P0-2 代码侧完成、TA-001.5 可用且 fail-closed；
- 全量回归 0 失败、ruff 绿、迁移可逆；
- **建议 Leader APPROVED（277a）**；M0 仍需 277b + 运维证据。
