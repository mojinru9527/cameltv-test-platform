# Batch AIQE-V162 Dev Kanban — V1.6.2 Hardening 整改

> 分支：`feature/aiqe-v162-hardening` | 基线：`2d2f508d5` | 日期：2026-11-28

## 交付切片进度

| # | Slice | 实现 | 自测 | 证据 | 状态 |
|---|---|:---:|:---:|:---:|---|
| S1 | FIX-001 Gate E 严格化 + validators + RV 测试 | ✅ | ✅ | ✅ | 完成 |
| S2 | FIX-002/003 产品 TC 框架 + ADR 0032 | ✅ | ✅ | ✅ | PARTIAL（无隔离 Test 执行） |
| S3 | FIX-004～008 产品/Agent/Benchmark/多端/回归 | ✅ | ✅ | ✅ | PARTIAL/BLOCKED（外部环境） |
| S4 | FIX-009/010 凭据与生产阶段 | ✅ | ✅ | ✅ | PARTIAL（轮换外部）/ VERIFIED（阶段语义） |
| S5 | FIX-011/012 provenance + 审计关闭 | ✅ | ✅ | ✅ | 完成 |
| S6 | FIX-013/014 Ruleset + Reviewer 身份 | ✅ | ✅ | ✅ | PARTIAL（线上 apply/真实 review 待办） |
| S7 | FIX-015 Manifest + Final Acceptance | ✅ | ✅ | ✅ | PARTIAL（GA 未签署） |

## 已知阻塞

- 产品 TC 真实执行：缺隔离 Test 环境/Secret（BLOCKED，不伪造 PASS）。
- 生产阶段 1–4 / rollback drill：仅原始 canary 记录，阶段 3/4 跳过 → NOT_RUN。
- 生产测试密码/Kibana 密码轮换：需账号 owner 在外部系统执行。
- 真实 Reviewer：需 MoojinR 对最终 SHA 提交 APPROVED review。
- Main Ruleset：合并后 apply `AIQE V1.6 Governance Gate` 并重新 capture。

## 批次记录

### 2026-11-28 — 实现与本地门禁完成

- 新增 `statuses.py`、`validators/`（runtime/product/platform/production/branch/provenance/acceptance/closure）。
- `release_verdict.py` 接入严格 Gate E/F/G；runtime `ga_ready=false` 不再签 GA。
- 产品 TC schema 2.0、`verify_product_tc_results.py`、Runner 合同、ADR 0032。
- AgentTask API E2E、Benchmark 逐样本复算/双人审批、多端状态、Defect 回归守卫。
- Credential Scanner 重写并 CLEAN；CI PG 密码改 Secret；生产阶段证据归一化。
- Evidence index provenance、audit closure 语义规则、Ruleset 精确 checks、Reviewer 身份校验。
- 本地：AIQE 1516 passed；全量 backend 2854 passed / 43 skipped（修复 1 个顺序依赖后复跑）。
- 发布判定：`RELEASE_CANDIDATE_BLOCKED`（GA 未签署）。
