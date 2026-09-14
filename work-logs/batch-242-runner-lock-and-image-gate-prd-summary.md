# Batch 242 — Runner 依赖锁收口与镜像构建门禁
> **Product (🟦)** | Date: 2026-09-14 | Status: Approved

## 0. 批次模式

`mode: full`（完整批次）——本批改变 runner/combined 镜像的依赖装配配置，
并向 required CI job 引入新的构建门禁，命中「新配置/新行为」判定。

## 1. 问题陈述

Batch 241 收口 AI split 拓扑时暴露出两个已知缺口，均已登记为 C 条件：

1. **C241-2**：`requirements.runner.lock` 是**死文件**。ADR-0031 声明 runner 使用它，
   但 Dockerfile 的 `builder` 阶段实际安装的是 `requirements.lock`。
   两个文件包集合完全一致（各 119 个 pin、0 个版本差异），差别只在头注释与
   `# via` 注解——即同一份依赖存在两份真相，必然漂移。
2. **C241-3**：required 后端 job **不构建镜像**。Batch 240 的三套 lock 因在 Windows
   上解析而丢失 linux-only 传递依赖（`secretstorage`/`jeepney`/`uvloop`），
   使 `api` 与 `ai-gateway` 镜像完全无法构建，却**全绿合入 main**。

此外侦察中发现一个加重问题：

3. `scripts/ci/test_batch59_quality_contracts.py` **未被任何 workflow 执行**，
   且其中 `backend_tests` 断言指向早已改名的 job（现为 `backend-clean-checkout`）——
   门禁契约测试本身已腐化，无法起到防护作用。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| runner 依赖真相来源 | 双份（Dockerfile 用 `requirements.lock`，ADR/tests 用 `runner.lock`） | 单一：`requirements.runner.lock` |
| runner 镜像依赖版本 | 119 pins | **不变**（0 版本漂移） |
| required job 覆盖 lock 平台解析 | 无 | 三个 lock 全部 Linux 全量解析校验 |
| required job 覆盖镜像构建 | 无 | `docker build --target api` |
| CI 门禁契约测试 | 未被执行 | 接入 `ai-delivery-policy.yml` |
| 门禁契约测试陈旧断言 | 1 处（job id） | 0 |

## 3. 非目标

- 不改变 API / AI Gateway 的依赖集与镜像内容。
- 不改变对外 API、前端、数据库 Schema。
- 不为 runner 增加新依赖，不升级任何版本。
- 不在本批构建/发布生产镜像（CI 只做 `api` target 冒烟）。
- 不重构 `pr-check.yml`（每日观测任务）的既有 `requirements.lock` 用法。

## 4. 验收标准

1. Dockerfile 只有 `builder-runner` 一个全量 builder 阶段，安装
   `requirements.runner.lock`；`runtime-base` 从其复制 venv。
2. runner 镜像构建成功，且安装版本与改动前一致（无 pin 差异）。
3. `main-quality-gate.yml` 的后端 required job：
   - 对 `requirements.{api,ai,runner}.lock` 执行 Linux 全量解析校验
     （`--require-hashes --dry-run`），任一步失败即 job 失败；
   - 执行 `docker build --target api`（context = 仓库根）；
   - job timeout 足以覆盖新增工作量。
4. `scripts/ci/test_batch59_quality_contracts.py` 全绿，并由
   `ai-delivery-policy.yml` 实际执行。
5. 新增断言覆盖上述 3 条，且用「删除步骤/改窄 timeout」可使其失败。
6. 既有部署/镜像契约测试保持绿色。

## 5. 用户价值

- 消除「同一依赖两份真相」，降低后续依赖升级漏改风险。
- 让「lock 能不能在 Linux 装」「镜像能不能构建」成为**合入门禁**而非人工发现，
  从根上堵住 Batch 240 那类 P0。
- 让已经腐化的门禁契约测试重新生效，避免 CI 门禁被静默削弱。
