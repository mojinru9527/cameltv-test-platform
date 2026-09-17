# Batch 250 — 发布护栏（Release Guardrails）PRD-lite

> **🟦 Product** | Date: 2026-09-17 | 分支：`feature/batch-250-release-guardrails`

```yaml
mode: light
豁免理由: |
  本批是「内部发布工具 + 既有缺陷修复」，不引入新接口、新配置、新依赖、新用户可见行为：
  - C249-1 给既有脚本加只读演练开关（-DryRun），默认行为不变；
  - C249-3 清理控制面既有测试目录的 lint 历史债（# noqa 标注 + 校验），无运行时行为；
  - C249-4 在既有发布事件里多写一段诊断文本，属于既有字段的填充强化。
判定依据: docs/agent-team/pipeline-modes.md「是否引入新行为/新接口/新配置/新依赖」→ 否。
```

## 1. 问题陈述（为什么用户/运维关心）

2026-09-17 一天内发布链路连出三次事故，全部与「不可演练、不可观测」有关：

1. **不可演练**：QA 为了实测一个函数（`Get-AlembicHead`）直接执行 `release.ps1`，
   而该脚本没有 dry-run 开关 → 立刻开始真实构建镜像，约 30 秒后才被人工终止（止损后核对：假 tag 制品 0 个、控制面记录 0 条）。
2. **不可构建自证**：控制面 `Dockerfile` 显式列举 `COPY`，Batch 249 新增的 `migrations.py` 未被拷贝 →
   直接部署会让"恢复平面"起不来（PR #464 修复）。
3. **不可观测**：迁移作业失败时，控制面事件只记 `publish failed`，远程只回
   `remote command failed rc=1: `（**后面什么都没有**）——运维无法判断是"迁移没生效"还是"别的地方挂了"，
   只能 SSH 上机手工 `alembic current` 对比，这正是 Batch 248 那场 500 事故的复盘缺口。

## 2. 成功指标

| # | 指标 | 判定 |
|---|------|------|
| M1 | 演练一次完整发布流程，零副作用 | 输出 `release-<tag>-dryrun-manifest.json`；无构建、无登记、无上传、无发布 |
| M2 | 控制面测试目录 lint 零告警 | `ruff check .` → All checks passed |
| M3 | 迁移校验无论成败都留下 target/current | 远程输出含 `CAMELTV_MIGRATION target=X actual=Y` |
| M4 | 迁移没生效时发布事件可判读 | `/api/deployments/{id}/events` 的 `PROD_FAILED.reason` 含 `migration target=X actual=Y` |
| M5 | 新护栏在真实发布中被走过一遍 | 一次真实发布验收：manifest 真实 revision + 迁移→校验→停旧→起新 |

## 3. 非目标（本批不做）

- **C249-2 已关闭**（控制面自身发布含迁移作业，PR #464 + `release-20260917` 镜像）。
- **C249-5**（沿用旧镜像前核对 `RUNNER_ENDPOINTS` 转发面 / 补丁镜像必须含 `alembic/versions`）仍 Open。
- **C249-6**（SKILL.md/DEPARTMENTS.md 补「合并前先比对两侧同名文件规模」）仍 Open，属流程文档回写。
- **C249-7**（控制面 Dockerfile 改 `COPY *.py ./` 或加守卫测试）仍 Open；本批只以真实构建验证其风险已被 PR #464 消解。
- 不修 runner target 本地可构建性（C248-8）。
- 不改控制面状态机/接口契约，不加 UI。

## 4. 用户故事与验收标准

### US-1（C249-1）运维/QA 要能安全演练发布

- **Given** 我需要在发布前核对 manifest（git sha、alembic head、digest 预览）
- **When** 我执行 `pwsh scripts/ops/release.ps1 -Tag release-YYYYMMDD-NNNN -RuntimeMode split -ExecutionConfig <file> -DryRun`
- **Then** 脚本打印 git SHA / alembic head / manifest 预览并写入 `<tag>-dryrun-manifest.json`，
  且**明确声明**「未构建、未登记、未上传、未发布」，不产生任何镜像与登记记录
- **And** 不带 `-DryRun` 时行为与既有发布完全一致（默认不回归）

### US-2（C249-3）维护者要能对控制面目录跑通 lint

- **Given** `deploy/release-console` 是独立可测试子项目（`tests/` 先 `sys.path.insert` 再 import）
- **When** 我执行 `ruff check .`
- **Then** 零告警（历史 E402 以显式标注处理，不靠关闭规则）

### US-3（C249-4）运维要在发布记录里直接看到「迁移没生效」

- **Given** 一次发布的迁移作业实际没把库升到 manifest 的 target revision
- **When** 控制面执行 publish 失败并落 `PROD_FAILED`
- **Then** 远程输出包含 `CAMELTV_MIGRATION target=X actual=Y`
- **And** `deployment_events.reason` 记录 `publish failed: migration target=X actual=Y`
- **And** 迁移实际成功时，`PROD_OBSERVING` 事件记录 `publish succeeded; migration target=X actual=X`（正向证据）
- **And** 失败发生在别处（无状态行）时事件 reason 不臆造迁移结论

## 5. 纳入本批的 C 条件

| ID | 内容 | 本批处理 |
|----|------|---------|
| C249-1 | `release.ps1` 增加 `-DryRun` | ✅ 实现 + 实测 |
| C249-3 | 控制面测试目录 E402 历史债清理 | ✅ 清理 + 全量 lint |
| C249-4 | 迁移失败可观测性：事件记录 target 与 `current` 差异 | ✅ 实现 + 单测 + 真实发布验收 |

## 6. 风险与对策

| 风险 | 等级 | 对策 |
|------|------|------|
| `-DryRun` 被误当作"发布成功"证据 | 中 | 输出显式打印「未构建、未登记、未上传、未发布」；本 PRD/QA 明确它只是演练 |
| split 模式 DryRun 缺 `-ExecutionConfig` 时会静默给出不完整 manifest | 中 | 缺文件即 `throw`（fail-closed），不产出半成品预览 |
| 事件 reason 写入异常文本导致审计噪音 | 低 | reason 截断至 300 字符；无 `CAMELTV_MIGRATION` 状态行时保持原样 |
| 真实发布验收需要本机 Docker + SSH 密钥 + 控制面令牌 | 中 | 合入后执行；证据（manifest/事件/远端日志）写入 QA 报告 |
