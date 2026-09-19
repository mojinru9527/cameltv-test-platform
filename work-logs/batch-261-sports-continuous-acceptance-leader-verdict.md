# Batch 261 — Leader Verdict

> **Leader (🎯)** | Date: 2026-09-19 | Decision: **有条件通过（1 条 C 条件）**
> 待用户一次总确认（推送 + Draft PR + required checks 通过后合入）后转 APPROVED。

## 评审摘要

| 维度 | 评分 | 备注 |
|------|:----:|------|
| 实现质量 | 良 | 判定逻辑全部可单测；拿不到的证据一律转 C 条件，零伪造 |
| 风险 | 低 | 无新迁移、无新执行/推理路径；凭据不入快照有测试守着 |
| 覆盖 | 良 | 后端全量 2922 例 0 失败；前端 168 文件 737 例；缺口是真实环境（C261-1） |
| 流程合规 | 良 | 完整批次六件齐全；看板/复盘卡/流程回写齐备；§5 九条验收报告已出 |

## 关键决策（已批准）

1. **B4 前三项按"证据可得性"切分**：B4-1（证据包定型）与 B4-2（数据集与基线机制）在批次内做完并给可执行证据；B4-3/4/5 交付**判定内核 + 演练驱动 + 报告模板**，真实数字留给有环境的机器（C261-1）。**不拿本地替身冒充体育 3 版本验收。**
2. **篡改过的证据不算满足必需证据**（不只是打个标记）：与既有 `EvidenceCompletenessPolicy` 的 V3.9-R1「物理可用才算完整」对齐，否则会出现"证据被改过、完整率仍 100%、放行照样成立"。
3. **完整性口径不新建第二套**：必需证据来自既有策略，有收敛断言守着——这是 S1/S5 那类"两份实现"的直接防线。
4. **B4-2 交付选择器而非写死的 50+30 清单**：本机库为空，写死清单等于凭空造数据；选择器在有环境的机器上可复现同一份清单，并且"够不够"可核对（`shortfall`/`meets_target`）。
5. **基线里绝不出现被测凭据（H3）**：账号只存槽位名，测试对快照做全文凭据词扫描。
6. **环境不足时驱动必须失败**：`drill_three_versions.py` 本机实测 exit 4 并列出 4 项阻塞，明确写"不会用本地替身顶替"。拒绝伪造的成本为零——这正是它值得先做的原因。

## 抽检通过

- ✅ `app/services/evidence_bundle_service.py:1-30` — 模块 docstring 写明"为什么篡改必须排除出必需证据"，与既有策略对齐。
- ✅ `app/services/evidence_bundle_service.py:verify_bundle` — 只把"完好且被识别"的文件计入 `usable_types`；`unclassified` 显式返回。
- ✅ `app/api/v1/execution_jobs.py` — verify 路由注册在 `/evidence/{name}` **之前**，并有测试断言其命中校验分支。
- ✅ `app/services/pilot_dataset_service.py:build_baseline` — 复用既有指纹算法；返回体只含槽位引用。
- ✅ `app/services/pilot_slo_service.py` — 4 项阈值 + 断档重计数；缺测量值为**不达标**而非默认为真。
- ✅ `scripts/drill_three_versions.py` — 前置不过 exit 4 且不执行任何版本（本机实测）。
- ✅ `pytest -q` 全量 — **2922 passed / 0 failed**；本批无新迁移。
- ✅ `quality_ratchet.py` — PASS（ruff/mypy increased_keys 均为 0）。
- ✅ 前端 `typecheck` / `lint` / `vitest`（168 文件 737 例）/ `build` — 退出码全 0。
- ✅ §5 九条验收报告 — `work-logs/batch-261-...-final-acceptance-report.md`，逐条给"怎么验 + 实测 + 证据"，拿不到的写拿不到。

## 判决

**有条件通过**：代码与工件达到合入标准，须满足下列条件且需用户一次总确认。

合入前置（不可跳过）：
1. 用户一次总确认（推送 `feature/batch-261-sports-continuous-acceptance` + 创建 Draft PR + required checks 全绿后合入 main）。
2. `pwsh scripts/git/audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor codex -RequireSuccessfulChecks` 通过。
3. `C-CONDITIONS.md` 记录 C261-1。

## 下一批次 Leader 条件

- **C261-1（P1）**：B4-3/4/5 的真实 3 版本 SLO 数字未产出——Test5 需 VPN（`C258-1`）、库内无体育资产（`C260-1`），本机前置检查实测 `not_ready`（数据集/指纹/节点/被测系统四项阻塞）。**解除条件**：在接 VPN 且库内有体育资产的机器上执行
  `python scripts/build_pilot_baseline.py …` 与 `python scripts/drill_three_versions.py …`
  （命令与参数见最终验收报告 §2 第 7 条），把 `baseline.json` / `drill-report.json` 回贴；判定由 `pilot_slo_service.compute_slo` 给出，达标即解除。

## 流程回写（Batch 75 起强制）

| 发现 | 处理 | 落点 |
|------|------|------|
| **backlog 的交付物写的是"结果"，但本机拿不到环境**（B4-2「资产导入完成」、B4-3/4/5「连续 3 版本 SLO」） | 本批把这三项切成"判定内核/驱动（可交付、可单测）"与"真实数字（C 条件）"两半，并让驱动在环境不足时**实测失败** | `work-logs/batch-261-...-prd-summary.md` §2 §6；这是 B1–B4 连续第四次"环境依赖必须在 PRD 阶段切开"的同一教训 |
| 「证据被篡改但仍算完整」是一个**跨批次累积**的放行漏洞（B1 落 manifest 时未做判定，既有 AITDE 策略也未被外部证据包复用） | 本批把两者收敛，并用测试钉住"篡改文件不计入必需证据" | `app/services/evidence_bundle_service.py`；`tests/test_batch261_evidence_bundle.py` |
| `app/modules/aitde/assertion/completeness.py` 的完整率策略与 `execution_evidence_store` 长期互不知晓——同类"能力存两份但都不完整"的模式在 B1/B2/B3 各出现一次 | 建议 Product 步骤固定加一问："这段能力是否**已存在但未被使用**？"（B1 的 outbound_policy、B3 的 B11/B12、B4 的 completeness 都是这类） | 建议写入 `cameltv-agent-team` SKILL.md 的 Product 节（改动需同批 CHANGELOG，故本批未改技能，留作后续） |
| 环境不可达在审计脚本层也会表现为"审计失败"（`audit-ai-pr.ps1` 内部 `git fetch`） | B3 已记录；本批复现一次，处理方式=用 `GIT_CONFIG_*` 直连覆盖重跑 | B3 Leader verdict 流程回写；本批未重复登记 |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 24h / ~20h | 0/0/0/3 | 1 | 需求（交付物写"结果"但环境不可得） | PRD 阶段就把环境依赖项切成"内核/驱动 + 真实数字"，并给驱动加"环境不足即失败"的实测 |

**技能使用**: `cameltv-bug-guard` → 三问与 H3/路径收敛核对（非测试证据）；`cameltv-agent-team` → 六部门工件与门禁（非测试证据）。
