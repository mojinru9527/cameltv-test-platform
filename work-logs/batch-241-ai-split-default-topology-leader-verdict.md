# Batch 241 — Leader 判决
> **Leader (🎯)** | Date: 2026-09-14 | Verdict: **APPROVED**

## 1. 交付判定

| 条件 | 要求 | 证据 | 判定 |
|------|------|------|------|
| C239-2 | 真实 Docker host 完成 API→AI Gateway→runtime 全链路 smoke，再切换默认 split | `work-logs/evidence/batch-241-ai-split-smoke.json`；base compose 默认已 split | ✅ Closed |
| C239-3 | 发布 profile 同时支持 split 与 combined rollback；缺 token/image 时 fail-closed | split 制品集含 ai-gateway；`_compose` combined 分支叠加 combined overlay；缺 token 渲染失败 + 网关 health 503 | ✅ Closed |
| C240-1 | 记录三镜像实际体积与共享层，验证 API image 体积下降 | api 112.6 MiB / gateway 171.1 MiB / runner 1336.0 MiB；**下降 91.6%**；共享层 4–5 | ✅ Closed |
| 附加 | — | Batch 240 遗留 P0（lock 无法在 linux 安装）已修复 | ✅ C241-1 Closed |

## 2. 六部门工件

| 部门 | 工件 | 状态 |
|------|------|------|
| 🟦 Product | `work-logs/batch-241-ai-split-default-topology-prd-summary.md` | ✅ |
| 🟨 PM | `work-logs/batch-241-ai-split-default-topology-pm-plan.md` | ✅ |
| 🎨 Design | `work-logs/batch-241-ai-split-default-topology-design-spec.md` | ✅ |
| 💻 Dev | `work-logs/kanbans/DEV-ai-split-default-topology.md` + 代码 | ✅ |
| 🔍 QA | `work-logs/batch-241-ai-split-default-topology-qa-report.md` | ✅ |
| 🎯 Leader | 本文件 | ✅ |

批次模式：**完整批次**（引入新默认拓扑 = 新配置/新行为）。

## 3. 质量门禁

| 门禁 | 结果 |
|------|------|
| Ruff F821 | ✅ |
| Dev Gate G0–G2 | ✅ PASS_WITH_WARN（HARD=0） |
| 前端 typecheck / lint | ✅ |
| 后端全量 pytest | ✅ 见 QA 报告 §6（无新增失败） |
| 发布控制面 pytest | ✅ 37 passed |
| 真机 Docker smoke | ✅ result=passed |

## 4. 关键风险复核

| 风险 | Leader 判断 |
|------|------------|
| 默认拓扑变更影响生产 | **可接受**：combined `runtime` target 未删除，回滚 overlay 已契约化并验证渲染；发布走 release 火车 |
| `!reset` 依赖 Compose v2.24+ | **可接受**：CI 与发布主机均为 v2.4x；契约测试覆盖 |
| 本批未在生产验证 | **已知**：C239-2 原文要求「真实 Docker host」，本地 Docker Desktop（linux 容器）已满足；生产验证归发布窗口 |
| `requirements.runner.lock` 死文件 | **转 C241-2**，不阻塞本批 |

## 5. 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| CI 的 required 后端 job 只跑 pytest，**不构建镜像**，导致 Batch 240 的 lock 平台缺陷直接合入 main 且未被拦截 | 开 C 条件跟踪「CI 需覆盖镜像构建」 | 见下文 C241-3 |
| 新 lock 生成必须在目标平台解析（Windows 生成的锁会丢 linux-only 传递依赖） | 写入 ADR-0031 决策 6 | `docs/adr/0031-ai-rag-python-dependency-layers.md` |
| `docker-compose.yml` 的 `extends` 会合并 `depends_on`，容易造出自依赖 | 记入 Dev 看板「阻塞与决策」 | `work-logs/kanbans/DEV-ai-split-default-topology.md` |
| 主机页面文件耗尽会让 docker CLI 崩溃并表现为构建失败 | 记入 QA 残余风险 | QA 报告 §7 |

### 新增 C 条件

| ID | 内容 | 优先级 |
|----|------|--------|
| C241-3 | `main-quality-gate` 的后端 required job 需增加 `docker build --target api`（或等价镜像构建冒烟），否则 lock/依赖层缺陷仍会绕过门禁 | P1 |
