# Batch 261 — PM Plan

> **PM (🟨)** | Date: 2026-09-19
> 对应 PRD: [batch-261-sports-continuous-acceptance-prd-summary.md](batch-261-sports-continuous-acceptance-prd-summary.md)

## 规格摘要

**原始需求**: `10-landing-plan-task-backlog.md` §2「B4」表 B4-1…B4-5。
**范围纪律**: 只做 B4 表内任务；**凡既有能力必须复用**（PRD §1 §4）：证据完整率口径复用 `EvidenceCompletenessPolicy`，指纹/账号槽位/版本记录复用既有模型。

## 开发任务

### [ ] Task 1: 证据包校验服务（B4-1 后端）
**描述**: 新增 `evidence_bundle_service.verify_bundle(job_id, attempt)`：重新计算每个文件的 sha256 与 manifest 比对 → 逐文件 `ok|tampered|missing`；检测 manifest 之外的 `extra` 文件；把证据文件名映射到既有 `EvidenceType`，**复用 `completeness.required_evidence` 判定必需证据是否齐备**（缺失清单返回给调用方）。
**关键语义**：**篡改过的文件不算满足必需证据**（与既有策略"物理可用才算完整"一致）——这是"改一字节 → 校验失败"能成立的关键，不能只在 verdict 上标记而仍算完整。
**验收标准**: 未改动 → `verified` + 完整；改一字节 → `tampered` + 列出该文件 + 该类型不算满足必需证据；缺文件 → `missing`；多余文件 → `extra`。
**涉及文件**: `app/services/evidence_bundle_service.py`（新）、`tests/test_batch261_evidence_bundle.py`（新）
**参考**: PRD §1 §5；既有 `aitde/assertion/completeness.py`

### [ ] Task 2: 证据校验 API + 篡改显红（B4-1 接口与前端）
**描述**: `GET /execution-jobs/{job_id}/evidence/verify?attempt=` 返回 verdict/逐文件状态/缺失必需证据/多余文件；前端新增 `EvidenceBundlePanel`：逐文件状态列表，**篡改与缺失用 destructive 语义显红**，并显示缺失的必需证据类型。
**验收标准**: API 可查；篡改条目在 UI 上为红色（`text-destructive`）；能力缺失时明确提示而非静默。
**涉及文件**: `app/api/v1/execution_jobs.py`、`frontend/src/api/executionJobs.ts`、`frontend/src/components/execution/EvidenceBundlePanel.tsx`（新）、前端测试
**参考**: PRD §5

### [ ] Task 3: 试点数据集与基线制备（B4-2）
**描述**: 交付"接口 50 + Web 30"的数据集**清单与导入路径**（复用 `scripts/import_sports_cases.py` 与 `scripts/sports/` 既有能力），以及环境指纹/账号槽位的接线说明与可执行校验。
**验收标准**: 清单与导入命令可复现；指纹生成/比对有可执行校验；账号槽位接线有测试。
**涉及文件**: `scripts/sports/` 或 `backend/scripts/`（清单/驱动脚本）、`app/modules/aitde/environment/fingerprint.py` 接线、测试
**参考**: PRD §2 §6

### [ ] Task 4: 连续 3 版本演练 + 验收报告模板（B4-3/4/5）
**描述**: 一条命令跑完 3 个版本：版本 1（执行 + 缺陷闭环 + 证据包）→ 版本 2（复用验证）→ 版本 3（SLO 统计），输出 §2.3 四项 DoD 的数字（≤1 人日、完整率 100%、复用命中率 ≥50%、连续 3 版）并生成验收报告骨架。
**不可伪造约束**: 脚本必须**如实标注环境**（目标系统、指纹、节点）并在不可达时明确失败，不得以本地替身冒充体育验收。
**验收标准**: 脚本在无环境时给出可读失败原因与前置检查清单；在有环境时产出上述数字。
**涉及文件**: `scripts/sports/`（演练脚本）、`work-logs/`（报告模板）
**参考**: PRD §2 §6

### [ ] Task 5: §5 九条验收报告（B4-5 收尾）
**描述**: 按 backlog §5 的 9 条输出验收报告，每条给"怎么验 + 实测结果 + 证据链接"，其中环境依赖项注明 C 条件与解除方式。
**验收标准**: 9 条齐全；无未标注的推测结论（拿不到的就写拿不到）。
**涉及文件**: `work-logs/batch-261-sports-continuous-acceptance-final-acceptance-report.md`（新）
**参考**: backlog §5

## 质量要求

- [ ] 单元测试覆盖  - [ ] 无障碍（ARIA/键盘）  - [ ] 无 console 报错/告警
- [ ] 每切片只 `git add` 本切片文件；新增路由同步 `tests/fixtures/route_inventory.json`
- [ ] **提交前本地跑 `python scripts/ci/quality_ratchet.py`** 与**后端全量 `pytest`**（B3 已验证：本地预跑可让 CI 一次全绿）
- [ ] 前端全量用 `--maxWorkers=2`（本机 OOM 已知）
