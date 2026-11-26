# Sprint 0 工程交付差距报告

> **STATUS: HISTORICAL** — 本文记录 2026-11-2x 当时的执行事实与结论；其中 PASS/VERIFIED 等表述不代表当前发布判定。当前状态以 `release-verdict.json`、`E2E-Coverage-and-Blockers.md` 与 `governance/production-evidence.json` 为准。


- 生成时间：2026-11-19
- 基线：`86a44b2cbb7c9c44d3ef6af1e324d1f42c3eae6f`
- 范围：Sprint 0（分支/环境/迁移基线/依赖/调用图/追踪矩阵/CI Gate）+ 进行中的 P0
- 依据：`docs/aiqe/v1.6/_audit/` 七份独立审计 + 追踪矩阵 + 本地门禁运行结果

> 本报告按 V16-025 §9 口径统计，**只报告状态与差距，不用“关闭 Issue 数量”代替验收**。
> `BLOCKED/SKIP/UNKNOWN/NOT_RUN` 均不计入通过率。

---

## 1. 基线事实

| 项 | 值 |
|---|---|
| origin/main HEAD | `86a44b2cbb7c9c44d3ef6af1e324d1f42c3eae6f`（= V1.5 审计快照） |
| release 分支 | `release/aiqe-v1-6`（worktree `F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6`） |
| worktree 元数据 | workflow=direct / executor=DeepSeek_Harness / ports 5189/8031 |
| 迁移 head | `20261119_v16_001_policy_status`（单头） |
| 依赖锁 | `requirements.txt` / `requirements.lock`（后续 V16-022 补齐 CI 使用） |
| 调用图 | 见 `V1.6-Architecture-and-Security-ADR.md` §ADR-V16-05 与追踪矩阵 `production_entry` |
| 追踪矩阵 | 41 条需求（V16-001～025 + TC-AIQE-001～010），YAML 为事实源 |

## 2. 计划需求 vs 状态

| 状态 | 数量 | 说明 |
|---|---:|---|
| VERIFIED | 7 | V16-001-R1～R5、V16-002-R1/R3 |
| IMPLEMENTED | 1 | V16-002-R2（容器 egress 未验证） |
| PARTIAL | 23 | V16-003～024（除已完成部分） |
| NOT_STARTED | 10 | TC-AIQE-001～010 |
| BLOCKED | 0 | — |
| ACCEPTED | 0 | 尚无独立验收签字 |
| **合计** | **41** | 通过率 = 7/41 = **17.1%**（仅计 VERIFIED/ACCEPTED） |

## 3. Gate 失败项

| Gate | 失败项 | 归属 |
|---|---|---|
| A | 依赖漏洞扫描未在本次采集 | CI / V16-022 |
| B | 容器 egress、Secret canary、DB 只读账号、跨项目拒绝 | V16-003/004/011/018/024 |
| C | 统一 Launch、QUEUED 必有 Job、DAG clone、Lease/Fencing、PASS 语义 | V16-005/006/007/009/020 |
| D | A0/A4/A5/A6、ToolRegistry | V16-010/012/013/014/019 |
| E | 十个 TC、VERIFIED Verification Run | V16-015/016/017 |
| F | 监控/告警/灰度/回滚演练 | V16-024 |
| G | Vertical Slice 完整链、ACCEPTED、独立验收 | V16-025 / QA |

## 4. 未覆盖测试

| 层级 | 缺口 |
|---|---|
| L1/L2 | V16-003～025 的负向/边界测试大部分未写（见矩阵 `gaps`） |
| L3 | 只有 V16-001/002 有正式入口 Runtime 证据；TC 0/10 |
| L4 | 全部未执行（设备、容器、生产灰度） |

## 5. 未关联证据的需求

V16-003～024 共 22 条需求的 `evidence` 仅有基线审计编号，无 commit/CI/Run ID；
在对应 Issue 实现并产生正式入口证据前，**不得升级状态**。

## 6. 本 Sprint 已完成

1. worktree/branch/基线/迁移头/单头校验就绪；
2. 七组独立审计（G1–G8，缺 G6 已补）与调用图证据归档；
3. 追踪矩阵（YAML + 自动生成 Markdown）+ Traceability Gate + CI workflow +
   CODEOWNERS + PR 模板强制字段 + evidence-index 生成器；
4. 静态门禁 `check_aiqe_v16_static_gates.py` 与迁移门禁 `check_aiqe_v16_migrations.py`；
5. V16-001（P0）与 V16-002（P0，除容器 egress）实现并通过正式入口测试。

## 7. 下一 Sprint 出口条件（照实施计划 §0.2.9）

- **安全阶段**：V16-003/004 真实入口负向测试通过，Secret canary 0，DB 写尝试被真实只读账号拒绝；
- **执行阶段**：V16-005～009 完成统一 Launch/DAG/Lease/Assertion 终态闭环；
- 未满足前，禁止开放 Noise/Regression 自动化验收与 Agent 结论参与业务决策。
