# Batch 76 — Leader Verdict（避坑清单自动化 + AGENTS.md 双档同步）

> **Leader (🎯)** | Date: 2026-08-04 | Decision: **APPROVED**（待用户 push 授权 + 二次确认后合入）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 需求聚焦 | PASS | mode: light 轻量批次，仅工具 + 文档；C74-1/2/3 与存量债务均未扩范围 |
| 证据 | PASS | SelfTest exit 0；真实扫描按设计阻断（67 HARD）；audit-cconditions exit 0 |
| 诚实性 | PASS | 首扫发现 Batch 37 两个 P0 未修复，如实上报并移交 C76-1，未粉饰 |
| 风险 | 低 | 只读扫描脚本 + 文档；不改变任何业务代码行为 |

## 关键决策（已批准）

1. **避坑从"读"到"拦"**：`scan-common-bugs.ps1` 成为提交前可执行门禁，HARD>0 必须处理或注明豁免（已写入 SKILL.md Dev 步骤）。
2. **AGENTS.md 双档同步（C75-4 关闭）**：§2.1.2 与 SKILL.md/pipeline-modes.md 措辞一致，门禁双源消除。
3. **存量债务登记**：67 处 HARD 为历史存量（含 R.err 7 处、seed 密码 print），不作为本批缺陷，列为 C76-1 下批修复。
4. **脚本降噪**：backend/scripts 运维脚本的 print 降为 WARN，避免误伤合法 CLI 输出。

## 抽检通过

- ✅ [scan-common-bugs.ps1](scripts/git/scan-common-bugs.ps1) — Parser 0 错；SelfTest PASS；真实扫描 exit 1 正确阻断
- ✅ [AGENTS.md](AGENTS.md) — §2.1.2 双档措辞与 pipeline-modes.md 一致
- ✅ [SKILL.md](.claude/skills/cameltv-agent-team/SKILL.md) — Dev 步骤含扫描门禁与豁免规则
- ✅ [bug-guard/SKILL.md](.claude/skills/cameltv-bug-guard/SKILL.md) — 关联新增工具
- ✅ [CHANGELOG.md](.claude/skills/cameltv-agent-team/CHANGELOG.md) — Batch 76 条目
- ✅ `git diff --name-only` — 仅声明文件

## 判决

**APPROVED**。变更集最小、证据驱动、无业务代码风险。可进入 push → Draft PR → 首轮 checks → 用户二次确认 → 合入流程。

## 下一批次 Leader 条件

- **C76-1（P1）**：修复 scan-common-bugs 扫出的存量 HARD：`R.err` 7 处（补 `def err` 或改 raise）、seed.py 密码 print（改 logger 不输出明文）、高危 except-pass 逐处加日志或传播。
- **C76-2（P2）**：后续批次提交前运行 `scan-common-bugs.ps1`，HARD>0 处理或注明豁免（与 SKILL.md Dev 规则一致，作为条件强制）。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 避坑清单只能靠"读"，无法机器拦截 | 新建只读扫描脚本 + 接入 Dev 步骤 | scripts/git/scan-common-bugs.ps1；SKILL.md Dev 步骤 |
| AGENTS.md 与 SKILL.md 双档措辞不一致（C75-4） | 同步 §2.1.2 | AGENTS.md |
| 真实仓库存在 Batch 37 P0 存量（R.err/密码 print） | 如实登记为 C76-1，不作为本批缺陷 | C-CONDITIONS.md |
| scripts 运维 print 干扰扫描 | 按角色降为 WARN | scan-common-bugs.ps1 |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 4h / 实际 2.5h | 0/0/0/1 | 2 | 工具链 | 扫描脚本先小夹具验证路径/字段再全量 |

**技能使用**: `cameltv-agent-team` 轻量批次流水线；`cameltv-bug-guard` 规则来源；`scan-common-bugs.ps1` 本批交付工具。
