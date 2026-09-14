# Batch 242 — Leader 判决
> **Leader (🎯)** | Date: 2026-09-14 | Verdict: **APPROVED**

## 1. 交付判定

| 条件 | 要求 | 证据 | 判定 |
|------|------|------|------|
| C241-2 | `requirements.runner.lock` 死文件需收口（接线或删除） | Dockerfile 阶段改名 `builder-runner` 并改用该锁；真机镜像对比 **+0.003%**（依赖零漂移）；119 包干净容器安装 + 关键模块 import 通过 | ✅ Closed |
| C241-3 | required 后端 job 需覆盖镜像构建，堵住 lock/依赖层缺陷 | 新增三套 lock 的 Linux 全量解析校验 + `docker build --target api`；timeout 15→30；契约测试断言并接入 CI | ✅ Closed |
| 附加 | — | 修复长期未被执行且断言腐化的门禁契约测试（`backend_tests` → `backend-clean-checkout`）并接入 `ai-delivery-policy.yml` | ✅ |

## 2. 六部门工件

| 部门 | 工件 | 状态 |
|------|------|------|
| 🟦 Product | `work-logs/batch-242-runner-lock-and-image-gate-prd-summary.md` | ✅ |
| 🟨 PM | `work-logs/batch-242-runner-lock-and-image-gate-pm-plan.md` | ✅ |
| 🎨 Design | `work-logs/batch-242-runner-lock-and-image-gate-design-spec.md` | ✅ |
| 💻 Dev | `work-logs/kanbans/DEV-runner-lock-and-image-gate.md` + 代码 | ✅ |
| 🔍 QA | `work-logs/batch-242-runner-lock-and-image-gate-qa-report.md` | ✅ |
| 🎯 Leader | 本文件 | ✅ |

批次模式：**完整批次**（改变镜像依赖装配配置 + 引入新的 CI 门禁）。

## 3. 质量门禁

| 门禁 | 结果 |
|------|------|
| Ruff F821 | ✅ |
| Dev Gate G0–G2 | ✅ PASS_WITH_WARN（HARD=0） |
| 前端 typecheck / lint | ✅ |
| 后端部署/镜像契约 | ✅ 29 passed |
| CI 门禁契约 | ✅ 20 passed, 34 subtests |
| 发布控制面 | ✅ 37 passed |
| 后端全量 pytest | ✅ 见 QA §6（无新增失败） |
| 真机 runner 镜像构建 | ✅ 成功 |

## 4. 关键判断复核

| 决策点 | 判断 |
|--------|------|
| 收口方向：改用 `runner.lock` 还是删除它？ | **改用**。两锁 119 pins、0 版本差异，改用后零漂移，且 ADR-0031 的「三锁三 target」架构得以成立；删除会留下「runner 依赖谁」的口径空洞。 |
| 门禁放哪：新增 job 还是并入既有 job？ | **并入**。仓库未启用 GitHub branch protection，required 语义由 `audit-ai-pr.ps1` 固定三角色名承载，新增 job 不会成为门禁。 |
| lock 校验为何不用 `--no-deps`？ | `--no-deps` 会跳过依赖解析，正好绕过 Batch 240 的失败模式（未 pin 的传递依赖）。必须全量解析。 |
| `hf-xet` 构建失败是否阻断？ | **否**。经干净容器复现证明锁与 Dockerfile 均正确，根因是本地 buildkit pip cache 被中断构建污染；`buildx prune -a` 后冷缓存构建成功。 |

## 5. 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 仓库未启用 GitHub branch protection，required 语义仅在 `audit-ai-pr.ps1` 中；新增 job 不会自动成为门禁 | 记入 ADR-0031 决策 10 与 QA §5.1，避免后续误把新增 job 当门禁 | `docs/adr/0031-ai-rag-python-dependency-layers.md` |
| CI 门禁契约测试文件可能长期无人执行而静默腐化 | 本批接入 `ai-delivery-policy.yml`；建议后续同类契约测试统一在该 workflow 注册 | `.github/workflows/ai-delivery-policy.yml` |
| `--mount=type=cache` 共享 pip 缓存会被中断构建污染，表现为「hash 不匹配」 | 记入 QA §7 调查记录与残余风险 | QA 报告 §7 |
| `--dry-run --require-hashes` 必须配全量解析（不可 `--no-deps`）才有效 | 写入 ADR-0031 决策 10 与 Design §3 | 同上 |

## 6. 下一批次建议

C 条件表中已无 P0/P1 待办（C241-2/C241-3 关闭）。建议后续关注：

- 观察本批门禁在真实 PR 上的耗时（后端 job 是否仍在 30 分钟内）。
- `requirements.lock` 现仅作约束源与文档基线，若后续无人再消费可评估收敛方式
  （但 `pr-check.yml` 与 `Dockerfile.local` 仍在用，暂不建议动）。
