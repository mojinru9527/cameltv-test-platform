# Batch 258 — Leader Verdict

> **Leader (🎯)** | Date: 2026-09-18 | Decision: **有条件通过（1 条 C 条件）**
> 待用户一次总确认（推送 + Draft PR + required checks 通过后合入）后转 APPROVED。

## 评审摘要

| 维度 | 评分 | 备注 |
|------|:----:|------|
| 实现质量 | 良 | 逐切片 TDD；三处「看起来对但实际错」的问题被测试/演练抓出并修复 |
| 风险 | 低 | 三条安全硬线闭合；数据模型变更可逆（迁移已演练 downgrade） |
| 覆盖 | 良 | 后端 94 例 + 前端 721 例 + 端到端演练 19/19；缺口是 Test5 真机（C258-1） |
| 流程合规 | 良 | 完整批次六件齐全；worktree/分支/看板/复盘卡/流程回写到位 |

## 关键决策（已批准）

1. **B1 按完整批次执行**，覆盖 `09` 方案 §6 的「轻量」标注：B1-4 命中新接口 + 数据模型 + 执行链路 + 权限模型四个触发器，按 `pipeline-modes.md` 以触发器为准。
2. **B1-1 做成收敛而非新造**：`outbound_policy` 早已实现 SSRF 能力却被两个调用点绕过；抽 `app/core/url_guard.py` 作唯一入口、`outbound_policy` 反向依赖，旧名全保留。S1 跨 98 个提交未关闭的根因是"两份实现、脆弱那份在被用"，只补一处调用点会复发。
3. **`JobLease` 内联而非独立成表**（偏离 `09` §3.2 的对象清单）：该行同时要求"沿用 AiJob 的 claim/heartbeat/stale 语义"，而 AiJob 的租约就是内联字段。独立租约表会造成同一份租约两处记账——正是 Batch 240–255 清理过的双栈漂移。B4 若需要"租约历史"证据链，再加追加式 `job_lease_events`，不必拆现有真源。**此项已记录在 Design spec §1.5 等后续复核。**
4. **B1 证据做最小口径**：只做落盘 + 逐文件 sha256 + 上传对账 + 可下载；篡改显红、完整率门禁、放行结论绑定 bundle 哈希留给 B4-1，边界写在 `execution_evidence_store.py` 模块 docstring。避免 B1 与 B4-1 各做一半。
5. **B1-7 用本地替身跑真链路，不伪造 Test5 结论**：Test5 需 VPN，`192.168.50.170:80` 实测不通；演练把"被测目标"替换为本地替身，但平台、节点 CLI、httpx、Chromium、迁移、证据对账全是真的，且**首轮演练就抓出 2 个 P1**（见 QA D1/D2）。真机验收登记 C258-1。

## 抽检通过

- ✅ `app/core/url_guard.py:78-92` — `assert_public_url` 逐条拒绝并给出中文原因；`resolver` 注入使离线测试与"已解析地址复用"都成立（同链路非幂等网络操作只做一次）。
- ✅ `app/services/requirement_source_service.py:66-92` — 白名单为"根域及其子域"匹配，`pingcode.attacker.tld` 结构上不可能被归入 provider。
- ✅ `app/models/execution_job.py:1-38` — 与 `AiJob` 并列、不合并；模块头写明内联租约的理由。
- ✅ `alembic/versions/20260924_batch258_execution_payload.py` — 单独一条迁移而非改上一条；理由（上一条对已存在表直接 return，塞新列会让已升级库漏列）写在 docstring。
- ✅ `app/services/execution_evidence_store.py:44-58` — 文件名显式拒绝路径成分，注释记录"`Path().name` 在 POSIX 不把 `\` 当分隔符"这一真实陷阱。
- ✅ `frontend/src/components/execution/NodeStatusCard.tsx:31-40` — 两个 effect 均有 cleanup；轮询常量与 DoD 断言绑定。
- ✅ `npm run typecheck` / `npm run lint` / `npm test` / `npm run build` — 退出码 0 / 0 / 0（721 例）/ 0。
- ✅ `pwsh scripts/git/scan-common-bugs.ps1` — HARD 0。

## 判决

**有条件通过**：代码与工件达到合入标准，但必须满足下列条件，且需用户完成一次总确认。

合入前置（不可跳过）：
1. 用户一次总确认（推送 `feature/batch-258-execution-node-protocol` + 创建 Draft PR + required checks 全绿后合入 main）。
2. `pwsh scripts/git/audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor codex -RequireSuccessfulChecks` 通过。
3. `C-CONDITIONS.md` 记录 C258-1（Test5 真机验收延期）并带解除条件。

## 下一批次 Leader 条件

- **C258-1（P1）**：B1-7 的「体育试点 8 条用例（5 接口 + 3 Web）在 Test5 真实跑通」未完成——本机需 VPN 才能到 `camel-api-gateway05.svc.elelive.cn`（实测 TCP 80 不通）。**解除条件**：在接 VPN 的测试人员机器上执行 `cameltv-node up`，对体育 16.x 资产跑 5 接口 + 3 Web 并留存可下载证据（截图 + 请求回放 + manifest sha256），把下载链接与 `df`/时间戳写回 work-logs。
- **C258-2（P2）**：B2 起执行沙箱必须覆盖"节点持有被测系统凭据"的场景——本批 H3 只在控制面成立（平台不存被测凭据），节点侧凭据存放与隔离归 B2-1 落地。

## 流程回写（Batch 75 起强制）

| 发现 | 处理 | 落点 |
|------|------|------|
| 方案把 `JobLease` 列为独立对象，但同行的"沿用 AiJob 语义"指向内联；两处措辞互斥，执行者会各自理解 | 改 `docs/platform-refactor/09-...md` §3.2 措辞（标注租约内联、独立租约历史表留给 B4 按需追加） | 下一批修改 `docs/platform-refactor/09-platform-landing-plan.md` §3.2（已登记，本批未改文档以避免与 PR 混提交） |
| B1-7 依赖 VPN/内网可达性，但 PRD 阶段没有任何"依赖与可达性探针"，直到最后一步才发现不可达 | 作为复盘卡"下次避免"动作；建议写进 `cameltv-agent-team` 的 Product 步骤（开工前跑探针并把不可达项登记为 C 条件） | `work-logs/batch-258-...-qa-report.md` 复盘卡；技能文件改动需同批 `CHANGELOG.md`，本批不动 SKILL.md |
| `cameltv-agent-team` 的 Agent Team 例外（§2.4）与"逐次 push 确认"并存时，在长批次里容易误判为"可以随时 push" | 无需处理：本批严格在总确认前零 push | — |
| 仓库无 `@testing-library/jest-dom`，但新写测试容易习惯性用 `toBeInTheDocument` | 无需处理（本批已按仓库既有风格改为 `toBeTruthy`/`toBeNull`） | — |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 16h / ~21h | 0/2/2/1 | 3 | 需求不清（B1↔B4-1 证据口径）+ 环境（代理/VPN） | Product 阶段先跑依赖探针（VPN/浏览器/代理），不可达项当场转 C 条件 |

**技能使用**: `cameltv-bug-guard` → 三问与风险表核对（非测试证据）；`cameltv-agent-team` → 六部门工件与门禁（非测试证据）。
