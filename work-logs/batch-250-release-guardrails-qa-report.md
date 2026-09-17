# Batch 250 — QA Report（发布护栏）

> **🔍 QA** | Date: 2026-09-17 | 立场：默认「需要改进」
> 分支：`feature/batch-250-release-guardrails`（base `93259a84`）| worktree：`F:\CamelTv-worktrees\codex-batch-250-release-guardrails`
> 变更范围：`scripts/ops/**`、`deploy/release-console/**`、`work-logs/**`（**未触碰** `test-platform-v2/backend|frontend`）

## 1. 结论

**PASS（可进入一次总确认）**，但 **M5（真实发布验收）尚未完成**，属合入后执行项——
理由：验收要用控制面的新代码，而控制面镜像必须先从 main 重建（与 Batch 249 的 C249-2 同样模式）。

| 指标 | 状态 |
|------|------|
| M1 演练零副作用 | ✅ 实测 |
| M2 控制面 lint 零告警 | ✅ 实测 |
| M3 迁移校验留下 target/current | ✅ 单测 + 命令构造验证 |
| M4 事件 reason 可判读迁移差异 | ✅ 单测（失败/成功两侧） |
| M5 真实发布验收 | ⏳ 合入后执行（见 §6） |

## 2. 硬门禁证据

| 门禁 | 命令 | 结果 |
|---|---|---|
| 控制面全量测试 | `cd deploy/release-console && python -m pytest tests -q` | **51 passed, 2 subtests passed**（Batch 249 基线 45 → 本批 +6） |
| 本批新增测试 | `pytest tests/test_migrations.py tests/test_console_manifest.py -q` | 迁移状态/诊断 5 例 + 事件 reason 2 例，全绿 |
| 控制面 lint（全目录） | `python -m ruff check .` | **All checks passed**（C249-3 关闭依据） |
| 控制面导入冒烟 | `python -c "import app, tencent_executor, migrations"` | `console imports ok: CAMELTV_MIGRATION` |
| `release.ps1` 语法 | PowerShell AST Parser | `release.ps1 syntax OK` |
| `release.ps1 -DryRun` 实测 | 见 §3 | 输出预览 manifest，**未构建/未登记/未上传/未发布** |
| 远端校验命令构造 | `migration_commands(compose, target=...)` 实测打印 | `migration_actual=$(... alembic current ...); printf 'CAMELTV_MIGRATION target=%s actual=%s\n' ...; test "${migration_actual}" = ...` |

> 说明：本批无后端/前端代码改动，`ruff check app --select F821`、`npm run typecheck/build` 按 AGENTS.md §4.2
> 「部署定义 / CI / docs / work-logs」分类**跳过重测试**；required contexts 仍须返回结果（合入前以 CI 实际分类为准记录）。

## 3. M1 — `-DryRun` 零副作用实测

```powershell
pwsh scripts/ops/release.ps1 -Tag release-20260917-0099 -RuntimeMode split `
  -ExecutionConfig test-platform-v2/deploy/docker-compose.execution.yml -DryRun `
  -OutputDir <temp>\batch250-dryrun
```

输出（关键行，全文见 §7 摘要）：

```
==> Git SHA: f186181d...
==> Alembic head: 20260922_ai_agent_token
==> DryRun：未构建、未登记、未上传、未发布
==> manifest 预览已写入 ...\release-20260917-0099-dryrun-manifest.json
```

预览 manifest 关键字段（与 Batch 249 的 ADR-0015 §4 契约一致）：

```json
"database": { "alembic_heads": ["20260922_ai_agent_token"], "target_revision": "20260922_ai_agent_token",
              "rollback_mode": "application-rollback-or-forward-fix" },
"execution_config_sha256": "7a612e43a5a8764d18b6411d1b9a74f7448a6a8eb5a4fa123f9485ac2151c77d"
```

**副作用核对（逐项实测，全部为空）**

| 检查 | 命令 | 结果 |
|---|---|---|
| 预览文件只落在指定临时目录 | `ls <temp>\batch250-dryrun` | 仅 `release-20260917-0099-dryrun-manifest.json`（1301 B） |
| 真实制品目录未被污染 | `ls F:\CamelTv-safe-backup\release-artifacts\*0099*` | 无 |
| 本地未构建镜像 | `docker images --format '{{.Repository}}:{{.Tag}}' \| grep 0099` | 无 |
| 控制面未登记发布记录 | 未调用 `/api/deployments`（脚本 DryRun 分支提前 return） | 无新记录 |

> 这正是 C249-1 要防的场景：Batch 249 的 QA 实测 `Get-AlembicHead` 时误触真实构建（30 秒内人工止损）。
> 本次同样的"想核对 manifest/revision"动作走 `-DryRun`，零副作用。

## 4. M3/M4 — 迁移失败可观测性验证

| 场景 | 输入 | 期望 | 实测 |
|---|---|---|---|
| 迁移没生效 | 输出含 `CAMELTV_MIGRATION target=20260922_ai_agent_token actual=20260915_plan_dispatch` | `PROD_FAILED.reason` = `publish failed: migration target=20260922_ai_agent_token actual=20260915_plan_dispatch` | ✅（`test_migration_mismatch_is_recorded_in_event_reason`） |
| 迁移验证成功 | 输出含 `... target=X actual=X` | `PROD_OBSERVING.reason` = `publish succeeded; migration target=X actual=X` | ✅（`test_verified_migration_is_recorded_in_event_reason`） |
| 失败在别处（无状态行） | `remote command failed rc=1: capacity rejected` | reason 保持 `publish failed`，不臆造迁移结论 | ✅ |
| manifest 无真实 revision | `{}` / 占位值 | 仍报出实际 current，不抛二次异常 | ✅ |

## 5. 缺陷清单

### 🟡 P2-1（本批发现并修复）迁移校验失败时远程无任何可判读输出
- **现象**：旧实现为 `test "$(alembic current | tail -1 | awk '{print $1}')" = <target>`，失败即 `rc=1` 且**无输出**，
  控制面事件只记 `publish failed` → 运维无法区分「迁移没生效」与「其它步骤失败」。
- **修复**：校验步骤先取实际 `current` 并 `printf 'CAMELTV_MIGRATION target=%s actual=%s'`，再断言；
  控制面解析该行并写入 `deployment_events.reason`（失败/成功两侧）。

### 🟡 P2-2（本批发现并修复）`-DryRun` 在 split 模式缺 `-ExecutionConfig` 时会产出不完整 manifest
- **现象**：`execution_config_sha256` 需要真实配置文件哈希；若不校验就预览，会得到"看起来能发布"的残缺 manifest。
- **修复**：DryRun 分支对 split 模式强制 `-ExecutionConfig` 存在（leaf file），否则 `throw`（fail-closed）。

### ⚪ P3-1（工具限制，已记录）本地无 POSIX shell，无法本地实跑远程校验片段
- **现象**：本机无可用 bash（WSL 无发行版），Docker 引擎未启动时也无法借容器执行；
  因此"这段 shell 在远端能否正确打印并失败"只能在真实发布时验证。
- **处置**：本批以单测锁定命令构造（含 `migration_actual`、`printf`、`test` 三段），
  并在合入后的真实发布里取远端日志作为最终证据（M5）；M5 未完成前不得宣称 C249-4 验收通过。

### ⚪ P3-2（范围外，已登记）控制面 Dockerfile 显式列举 COPY
- PR #464 已补 `migrations.py`；根因（新增模块必须同步 COPY）登记为 **C249-7**，不在本批。

## 6. M5 — 真实发布验收（合入后执行，未完成）

计划步骤与预期证据：

1. 从 main 重建 `cameltv-release-console` 镜像并同参数换容器（保留 `:release-20260917` 回滚锚点）。
2. 用 `release.ps1 -Tag release-20260917-0006 -RuntimeMode split -ExecutionConfig test-platform-v2/deploy/docker-compose.execution.yml -Publish` 做一次真实小版本发布。
3. 预期观测：manifest `database.target_revision` 为真实 revision；远端日志顺序为 **迁移 → 校验 → 停旧 → 起新**；
   日志含 `CAMELTV_MIGRATION target=X actual=X`；`/api/deployments/{id}/events` 的 `PROD_OBSERVING.reason` 含同一对 revision。
4. 证据落 `work-logs/batch-250-release-guardrails-production-evidence-20260917.md`。

> 引用基线：容量/回滚/健康检查口径复用 `work-logs/batch-248-local-ai-agent-production-evidence-20260917.md`；
> 本批只跑增量（迁移顺序 + 事件 reason）。

## 7. 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 3h / 实际约 2h（不含发布验收） | 0/0/2/2 | 1（C249-4 从"只记失败"扩展为失败+成功两侧证据） | 工具链 + 流程 | 发布路径的任何新命令，先在 `-DryRun`/单测里锁住命令构造，再上生产 |
