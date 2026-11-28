# Batch AIQE-V162 — PM 执行计划

> PRD：`work-logs/batch-v162-aiqe-hardening-prd.md`
> 基线：`2d2f508d5d1fd452972e7af49d9b4f3bde2e7b01`；分支：`feature/aiqe-v162-hardening`

## 1. 切片与依赖

| 切片 | 内容 | 依赖 | 交付状态判据 |
|---|---|---|---|
| S1 | FIX-001 严格 Gate E + validators + RV-001～012 | 无 | RV 全绿；`--require-ga` 负例退出 1 |
| S2 | FIX-002/003 产品 TC 框架 + ADR 0032 | S1 状态模型 | 配置无解释 null=0；verify 拒绝伪造 |
| S3 | FIX-004～008 产品场景/Agent/Benchmark/多端/回归 | S2 | 正向 + 反向测试；无环境 BLOCKED |
| S4 | FIX-009/010 凭据与生产阶段 | 无 | 明文=0；阶段跳过不为 PASS |
| S5 | FIX-011/012 provenance + 审计关闭 | S1 | Builder 不覆盖 SHA；CLOSED 语义验证 |
| S6 | FIX-013/014 Ruleset + Reviewer 身份 | S5 | 精确 check；身份字段/API 校验 |
| S7 | FIX-015 最终验收、Manifest、报告 | S1–S6 | 精确 SHA 门禁 + 未完成项清单 |

## 2. 质量门禁（本地必须执行）

```powershell
cd test-platform-v2/backend
python -m pytest tests -q -k "aiqe"
python scripts/aiqe/check_traceability.py --strict-warnings --check-baseline
python scripts/aiqe/check_release_audit.py
python scripts/aiqe/check_audit_closure.py --check
python scripts/aiqe/run_product_tc.py --check-config
python scripts/aiqe/release_verdict.py --require-ga   # 预期非零（GA 未签署）
```

## 3. 交付顺序

1. 代码与测试全部通过本地门禁；
2. 生成 release-verdict / audit closure / credential scan / production evidence；
3. 生成 Evidence Manifest 与 Final Acceptance；
4. 一次总确认后 push 功能分支、创建 Draft PR；
5. required checks 全绿后合并 main；
6. 更新 Main Ruleset 增加 `AIQE V1.6 Governance Gate`，采集规则快照；
7. 更新精确 SHA 上的最终证据与报告；仅在全部强制 Gate PASS 时才允许 GA tag。

## 4. 明确阻塞（不可由本批次伪造）

| 阻塞 | Owner | 解除条件 |
|---|---|---|
| 产品 TC 隔离 Test 环境 / Secret / Runner | qa-team | 提供环境、Secret handle、可执行入口 |
| 生产测试账号密码轮换 | 账号负责人 | 在凭据系统完成轮换并登记事件 ID |
| 生产 canary/dogfood/rollback drill | ops | 在发布窗口执行并归档原始观测 |
| 真实非作者 GitHub Review | MoojinR | 对最终 SHA 的 PR 提交 APPROVED review |
| GA 签署 | 项目负责人 | A–G 全部 PASS + 上述证据齐全 |
