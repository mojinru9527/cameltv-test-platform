# Batch 98 — Leader Verdict（CI 迁移 + V1 工具删除）

> **Leader (🎯)** | Date: 2026-08-05 | Decision: **APPROVED**（待 required checks 全绿）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 需求聚焦 | PASS | 完整批次（mode: full），范围=CI 迁移 + 11 工具删除 + C64-3/C96-1 关闭，无蔓延 |
| 实现质量 | PASS | 自包含脚本三子命令实测；workflow 无 `tp` 引用；V1 引用全清理 |
| 证据 | PASS | G1–G9 门禁退出码齐全；脚本本地实测（health/run/collect-elk） |
| 诚实性 | PASS | prod smoke 行为变化如实登记；C27 四项保持 Open；V1 web-ui/server 留给 Batch 99 |
| 门禁 | PASS | audit 0 硬错、boundary PASS、引用扫描 0、保鲜 0 |
| 风险 | 中→低 | CI 变更触发双端全量回归；已按混合分类保守执行，合入前核验 required contexts |

## 关键决策（已批准）

1. CI 迁移方案：`scripts/ci/api-regression.ps1`（health/run/collect-elk）+ Playwright 直跑生成式用例；JUnit 以 artifact 承接；不再依赖 V1 本地报告看板。
2. prod smoke 由 `--grep smoke`（空跑）改为实际执行 6 个只读 spec（修复空跑，PRD 已登记）。
3. 11 个 V1 工具目录删除；`cli/tp.py` 保留 config 自检；V1 server 中 3 条依赖已删工具的路由移除。
4. C64-3 关闭（prod 业务 DB/Redis 无法提供，验收以 test 环境为准，同 C31-3 口径）；C96-1 的 V1 删除部分关闭。

## 抽检通过

- ✅ 两条 workflow 无 `tp ` 命令，YAML 解析通过
- ✅ 脚本三子命令本地实测（health 200×2 / run 18 用例+JUnit / collect-elk traceId）
- ✅ `rg` 可执行引用 0 命中；boundary PASS
- ✅ audit-cconditions -RequireLatestBatch exit 0（Open=23 / Closed=131）

## 判决

**APPROVED**：进入一次总确认 → push → Draft PR → required checks（双端全量）全绿 → 最终审计 → 合入 main。

## 下一批次 Leader 条件

- 不新增 C 条件。Batch 99：V1 `web-ui`/`server`/`cli` 覆盖矩阵退役（沿用 C64-1 剩余 + repo-boundaries deprecated-v1 规则）。
- C96-1：C27 四项验证（staging/本地全栈）待数据与性能测量。
- C95-1/C74-2：Test5 环境恢复后补拉 konfi/admin-service 契约。
- CP-C2/C84-1：iOS 真机执行结果登记。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| Batch 96 审计未覆盖 CI workflows 与 V1 server 引用 | 本批先迁移后删除；`rg` 0 引用为出口标准 | scripts/ci/api-regression.ps1 + server 路由清理 |
| 生成式目录无 lockfile，`npm ci` 失败 | 脚本自动降级 `npm install` | scripts/ci/api-regression.ps1 + B98-Q1 |
| PowerShell XML 适配器对嵌套 testsuite 取不到 | 改用 XPath `//testcase` | scripts/ci/api-regression.ps1 |
| prod smoke 空跑（grep 不匹配任何用例） | 移除 grep，实际执行只读 spec | api-regression.yml / prod-smoke-test.yml |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1d / 实际 1d | 0/0/0/3 | 2 | 工具链 | 新脚本三子命令先实测；删除前全仓引用扫描含 server/scripts |

**技能使用**：`cameltv-agent-team`
