# Batch 261 — QA 报告

> **QA (🔍)** | Date: 2026-09-19 | Verdict: **PASS（附 1 条 C 条件）**
> 批次档位：完整批次（六件）。范围：`docs/platform-refactor/10-...backlog.md` §2 的 B4-1…B4-5。

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 5（B4-1…B4-5） | 3 | 0 | 2（B4-3/4/5 的真实 3 版本数字需环境 → C261-1） |

## 可执行门禁

### 后端

| 命令 | 退出码 | 摘要 |
|------|:------:|------|
| `python -m ruff check app/ --select F821` | 0 | All checks passed! |
| `python -c "import app.main"` | 0 | import OK |
| `python -m alembic heads` | 0 | 单头（本批**无新迁移**，复用既有表） |
| `python scripts/ci/quality_ratchet.py` | 0 | **QUALITY_RATCHET=PASS**（ruff/mypy increased_keys 均为 0） |
| `pytest tests/test_batch261_*.py tests/test_route_inventory.py` | 0 | 45 passed |
| 影响面查询时延（试点规模合成数据，一次性测量） | 0 | 50 模块 / 80 用例 / 90 边 → 5 次取中位 **4.0ms**（min 3.8 / max 7.4），DoD 阈值 2000ms → PASS |
| **`pytest -q`（全量，CI 后端 required 同命令）** | 0 | **2922 passed, 52 skipped, 1 xfailed, 0 failed**（12:49） |
| `python scripts/build_pilot_baseline.py`（空库冒烟） | 3 | **如实报缺口**（shortfall api 50 / web 30），不凑数 |
| `python scripts/drill_three_versions.py`（本机冒烟） | 4 | **如实报 not_ready** 并列出 4 项具体阻塞；未执行任何版本 |

### 前端

| 命令 | 退出码 | 摘要 |
|------|:------:|------|
| `npm run typecheck` | 0 | `tsc -b` 无错误 |
| `npm run lint` | 0 | `eslint . --max-warnings=0` 无告警 |
| `npx vitest run --maxWorkers=2` | 0 | **168 文件 / 737 例全绿** |
| `npm run build` | 0 | `✓ built in 12.04s` |
| **`npm run test:a11y:ci`（Playwright + Chromium，与 CI 同命令）** | 0 | **28 passed（39.4s）**：login/a11y 基线 + batch61 键盘·响应式·axe 基线（多路由 × desktop/tablet/mobile）+ batch245 认证首页视觉 |

> a11y E2E 在**无后端**下运行（preview 静态构建）：日志中可见 `/api/v2/health` 代理 `ECONNREFUSED 127.0.0.1:8018`，属预期（worktree 后端未启动），用例按未登录/访客态断言并通过。
> 该套件**不断言一级导航数量**——导航计数断言位于 vitest 模型层（`nav-config.test.ts` 的 `PRIMARY_ENTRY_LIMIT`、`KnowledgeTabs.test.tsx` 的「恰好 3」），二者互为补充，见「发布建议」中的残余缺口。

## 逐条件验证

### 全量结果

```
python -m pytest -q -p no:cacheprovider
→ 2922 passed, 52 skipped, 1 xfailed, 0 failed in 769.36s (12:49)   exit 0
```

比 B3 的 2885 例多 37 例（本批新增：B4-1 17 + B4-2 9 + SLO 11）。

### B4-1 证据包定型 ✅ PASS
**变更**: `evidence_bundle_service.py`（新）、`execution_jobs.py`（verify API）、`EvidenceBundlePanel` + `LocalExecutionEvidenceSection`（前端）
| 检查项 | 结果 | 说明 |
|--------|------|------|
| manifest sha256 + 完整性校验 | ✅ | 逐文件 `ok/tampered/missing`；检测清单外 `extra` 与未识别 `unclassified` |
| 改一字节 → 校验失败 | ✅ | verdict=`tampered` + 列出该文件 + **该证据不再满足必需证据** |
| 完整性口径复用既有策略 | ✅ | 必需证据来自 `completeness.required_evidence()`，有收敛断言守着（不新建第二套） |
| 篡改显红（用户可见） | ✅ | 篡改/缺失行 `text-destructive` + 顶部汇总「已不作为放行证据」+ 单独列缺失类型 |
| 路由不被 `{name}` 抢匹配 | ✅ | verify 注册在 `/evidence/{name}` 之前，并有断言（返回校验结构而非文件内容） |

### B4-2 试点数据集与基线 ✅ PASS（真实度量 → C261-1）
**变更**: `pilot_dataset_service.py`（新）、`scripts/build_pilot_baseline.py`（新）
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 选择器确定性 | ✅ | 同库同参数必得同一清单；P0 优先、按 id 兜底排序 |
| 不足目标如实报 | ✅ | `shortfall` + `meets_target=false`；脚本空库 exit 3 |
| 环境指纹可复现 | ✅ | 复用既有 `compute_fingerprint_hash`；同因子同哈希、因子变则哈希变 |
| **凭据不入基线（H3）** | ✅ | 只存槽位名；测试用 JSON 全文扫描 6 类凭据词 |
| 真实导入完成 | ❌ | 本机库无体育资产 → **C261-1**，未伪造 |

### B4-3/4/5 连续 3 版本 SLO ⚠️ 交付内核与驱动，真实数字待环境（C261-1）
**变更**: `pilot_slo_service.py`（新）、`scripts/drill_three_versions.py`（新）
| 检查项 | 结果 | 说明 |
|--------|------|------|
| SLO 判定可单测 | ✅ | 11 例：4 项阈值、断档重新计数、缺测量不放过、空输入不谎报成功 |
| 无建议帧不蒙混 | ✅ | 无复用建议时 `hit_rate=None` 且不算达标 |
| 前置检查可读 | ✅ | 6 项检查翻译成"具体缺哪一环"，并写明"不会用本地替身顶替" |
| 环境不足时不继续 | ✅ | 本机冒烟 exit 4、未执行任何版本、列出 4 项阻塞 |
| 真实 3 版本数字 | ❌ | 需 VPN + 体育资产；本批不伪造 |

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|:------:|------|------|------|
| D1 | P3 | `EvidenceBundlePanel` 引用了未导出的图标 `ShieldAlert` | typecheck 前人工核对图标导出 | ✅ 改用 `ShieldCheck` |
| D2 | P3 | 新增 verify 路由后路由基线漂移（684→685） | `test_route_inventory` FAIL | ✅ 重新生成基线（diff 仅 +1 条） |
| D3 | P3 | 前端全量 vitest 在本机 OOM（环境限制，沿用 B2 记录解法） | — | ✅ `--maxWorkers=2` 全绿 |

无未修复缺陷。

## bug-guard「未关闭已知风险」表核对（每批必答三问）

**1) 本批是否新增了清单中的任一项？** 否。
- 本批无"用户输入 → 出网/落盘/执行代码"的新路径：证据校验只**读**已落盘文件并比对哈希；试点选择器只**读**用例表。
- 新写路径只有基线文件输出，且已由"凭据不入快照"测试覆盖。

**2) 本批是否修复/关闭了其中任一项？** S1–S5 已于 B1/B2 关闭；S6 **部分关闭**（`C259-2` 仍挂）。
- 本批对 S6 的增量贡献：证据完整性判定改为"**物理可用/未被篡改才算**"，与既有策略一致，堵住"证据被改过仍可达标"的口子。

**3) 本批新增的「外部输入 → 出网 / 落盘 / 执行代码」路径，是否都过了对应铁律？** 是（且本批基本无此类新路径）：
| 路径 | 铁律 | 校验 |
|------|------|------|
| 证据校验读取文件 | 路径必须收敛（不得越权读） | 复用 `execution_evidence_store` 的 `is_relative_to` 收敛 + 文件名白名单 |
| 基线写入 | 不得含被测系统凭据（H3） | JSON 全文扫描 6 类凭据词（测试） |
| 演练驱动发起执行 | 环境不可达时必须失败而非降级 | 本机冒烟 exit 4 + 阻塞清单（实测） |
| 控制面职责边界 | 不跑浏览器/模型/存凭据 | 本批无新增执行或推理路径；凭据只在节点侧 |

## CI 分层核对

本 PR 改动 `test-platform-v2/backend/**` + `test-platform-v2/frontend/**` + `scripts/**` + `work-logs/**` + `C-CONDITIONS.md`
→ 前后端 required 都会实跑，**不存在跳过**。

## 发布建议

**文档保鲜（AGENTS.md §3.3）**：本批新增 3 个可执行脚本（`build_pilot_baseline.py`、`drill_three_versions.py`，
以及 B1/B3 起就存在但一直未记录的 `cameltv_node/cli.py`、`backfill_impact_edges.py`），此前**均未写入 `COMMANDS.md`**——
属于"命令变了但文档没跟上"的自查项遗漏。本次已在 `COMMANDS.md` 新增 §8（本地执行节点）与 §9（知识与验收脚本），
含命令、退出码语义与指向验收报告的入口。

状态：**READY**（B4-1/B4-2 全绿；B4-3/4/5 交付内核与驱动，真实数字按实登记为 C261-1）
必修复：0　建议修复：0

**残余证据缺口（如实披露）**：B2-6 的 DoD 写「导航项 **E2E** 断言 ≤4」，本仓现有 Playwright 套件**没有**断言一级导航数量；
该断言实现在 vitest 模型层（`nav-config.test.ts` / `KnowledgeTabs.test.tsx`，随 CI 前端 required 运行）。
浏览器层 E2E 已覆盖 a11y/键盘/响应式基线（28 例通过），但「登录 tester → 数一级导航」这种**需后端会话**的 E2E 本批未新增——
若要补齐，需一个带后端的 E2E job，建议随 B5/后续批次排期（避免把"模型断言"表述成"浏览器 E2E"）。

**行为变更提示**：
1. 新增 `GET /execution-jobs/{job_id}/evidence/verify`（`execution:view`）；
2. 执行记录页新增「本地节点执行证据」区（默认不预取校验结果，点击才请求）；
3. 新增两个可执行脚本：`scripts/build_pilot_baseline.py`、`scripts/drill_three_versions.py`（本批**无数据库迁移**）。

## 复盘卡（Batch 75 起强制）

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 24h / ~20h | 0/0/0/3 | 1 | 需求（backlog 的 B4-2/B4-3 交付物写的是"结果"，而本机拿不到环境） | 环境依赖项在 PRD 阶段就切成"内核/驱动"与"真实数字"两半，并给驱动加"环境不足即失败"的实测（本批已这样做，效果是拒绝伪造成本为零） |

**技能使用**: `cameltv-bug-guard` → 三问与 H3/路径收敛核对（非测试证据）；`cameltv-agent-team` → 批次档位与工件骨架（非测试证据）。
