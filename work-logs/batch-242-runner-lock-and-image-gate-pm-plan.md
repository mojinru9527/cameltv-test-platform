# Batch 242 — PM 任务计划
> **PM (🟨)** | Date: 2026-09-14 | Status: Approved

## 1. 范围

| ID | 任务 | 关联条件 | 交付物 |
|----|------|---------|--------|
| T1 | runner/combined 阶段改用 `requirements.runner.lock` | C241-2 | `backend/Dockerfile` |
| T2 | required 后端 job 增加 lock Linux 解析校验 | C241-3 | `.github/workflows/main-quality-gate.yml` |
| T3 | required 后端 job 增加 `api` 镜像构建冒烟 | C241-3 | 同上 |
| T4 | 修复并接入门禁契约测试 | C241-3 | `scripts/ci/test_batch59_quality_contracts.py`、`.github/workflows/ai-delivery-policy.yml` |
| T5 | 契约断言补齐 | T1–T4 | `backend/tests/test_deploy_compose_contract.py`、`scripts/ci/test_batch59_quality_contracts.py` |
| T6 | 真机验证 T1 不改变镜像内容 | T1 | `api`/`runner` target 构建 + 版本对比 |

## 2. 依赖与顺序

```
T1 ──> T5 ──> T6
T2/T3 ──> T4 ──> T5
```

- T1 与 T2/T3 相互独立，可并行。
- T6 是 T1 的验收硬门：**必须证明 runner 镜像依赖版本无漂移**，
  否则「收口死文件」会退化成「换了一份锁导致镜像变化」。

## 3. 风险与缓解

| 风险 | 等级 | 缓解 |
|------|------|------|
| 换锁后 runner 镜像内容变化 | 中 | 版本级 diff 已确认 0 差异；真机构建 + smoke 复验 |
| CI 时长上升导致 timeout | 中 | job timeout 15→30；lock 校验用 `--dry-run` 不落盘安装 |
| 镜像构建在 CI 冷缓存下过慢 | 低 | 只构建最轻的 `api` target；ai/runner 由 lock 解析校验覆盖 |
| 接入契约测试后暴露其他陈旧断言 | 中 | 已全量跑通再接入；陈旧断言按现行事实修正 |

## 4. 里程碑

| 里程碑 | 出口条件 |
|--------|---------|
| M1 锁收口 | Dockerfile 仅存 `builder-runner`，安装 `requirements.runner.lock` |
| M2 门禁落地 | 三个 lock Linux 解析通过 + `api` 镜像构建通过 |
| M3 契约生效 | 契约测试接入 CI 并全绿 |
| M4 交付 | required checks 全绿 + 最终审计 + Leader APPROVED |

## 5. 明确不做

- 不升级/新增依赖。
- 不改 API / AI Gateway 镜像。
- 不动 `pr-check.yml`、`Dockerfile.local` 的既有 `requirements.lock` 用法。
