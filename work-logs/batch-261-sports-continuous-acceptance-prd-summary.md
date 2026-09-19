# Batch 261 — PRD Summary

> **Product (🟦)** | Date: 2026-09-19 | Status: Review
> **批次档位**: 完整批次（六件）

## 0. 批次模式判定

```text
mode: full
判定依据: 数据模型/协议变更（证据包定型 + 完整性校验）+ 新接口（证据校验 API）+ 新配置（试点数据集与账号槽位）
豁免记录: 无
```

## 1. 问题陈述

09 方案 §2.3 的试点完成定义要求「单版本 ≤1 人日、证据包完整率 **100%**、复用命中率 ≥50%、**连续 ≥3 个版本**达标」。
本批（B4）是整条落地方案的最后一段，也是唯一以**真实执行数据**为交付物的一段。

开工前只读侦察（`main@3788c66d`）确认：**B4 同样以"收敛复用"为主，不是从零建**。

| B4 任务 | 已存在的底座 | 与 B4 的关系 |
|---|---|---|
| B4-1 证据包定型 | `aitde/assertion/completeness.py` 的 `EvidenceCompletenessPolicy`：按 `(adapter, oracle)` 定义必需证据（API→REQUEST+RESPONSE、UI→SCREENSHOT+CONSOLE…），且 V3.9-R1 已加固为**物理可用才算完整**（sanitized + hash-valid + 非空 + 存储存在；0 字节/空 hash/存储缺失都不算） | 策略已存在，**复用它**；缺的是「外部证据包（manifest）与这套策略对接」+ 篡改检测的用户可见路径 |
| B4-1 证据包（B1 已有） | B1 落的 `execution_evidence_store`：按 (job, attempt) 落盘 + 逐文件 sha256 manifest + 路径收敛下载 | 当时明确写了"篡改显红/完整率门禁留给 B4-1"——本批兑现 |
| B4-2 环境指纹 | `aitde/continuous/models.py` 的 `EnvironmentFingerprint`（`fingerprint_hash` + `components_json` + `confidence: LOW/MEDIUM/HIGH` 区分"探测 vs 手工声明"，按 `(environment_id, hash)` 唯一） | 直接复用，不新建指纹模型 |
| B4-2 账号槽位 | `services/session_credentials_service.py` | 直接复用 |
| B4-2 体育资产 | `scripts/sports/` 的导入/校准/基线脚本；`backend/scripts/import_sports_cases.py` | 复用既有导入入口 |
| B4-3/4/5 连续验收 | `ExecutionCampaign` / `CampaignScenario` / `RunProfile` / `QualityGatePolicy` / `QualityGateResultRecord`（AITDE v3.5 连续验收） | 版本序列与门禁已建模，不新建"验收栈" |

**结论**：B4 = 「把既有策略/模型/记录接成一条可跑的验收链」+「真实跑出 3 个版本的数字」。
凡是已存在的必须复用；重复造会立刻形成第二份实现——审计 S1/S5 的同一失败模式。

## 2. 环境事实（必须写进 PRD，因为它决定 B4 能交付到哪一步）

| 前提 | 实测 | 影响 |
|------|------|------|
| 到 Test5 网关的可达性 | `camel-api-gateway05.svc.elelive.cn` → `192.168.50.170`，**TCP 80 不通**（需 VPN） | B4-3/4/5 的"真实执行"在本机不成立 |
| 库内体育资产 | 本机 worktree 库为空，无体育 16.x 资产 | B4-2 的"资产导入完成"只能制备脚本与清单，不能产出真实覆盖率 |

因此本批的交付边界**按证据可得性切开**（详见 §6 与 C 条件）：
**B4-1（证据包收敛 + 篡改检测）与 B4-2（试点数据集/基线制备 + 指纹/账号槽位接线）在这里做完并给可执行证据；
B4-3/4/5 交付"一条命令跑完 3 个版本的演练 + 验收报告模板"，真实数字在接 VPN 的环境产出后回填。**
绝不拿合成数据或本地替身冒充"3 个版本跑通、SLO 达成"——那是伪造验收结论。

## 3. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 篡改可见性 | 无 | 改一字节 → 校验判定 `tampered` 且该文件**不再满足必需证据** | 本批 |
| 证据包完整率口径 | 无统一判定 | 复用 `EvidenceCompletenessPolicy`，按 (adapter, oracle) 判定并在 API 返回缺口清单 | 本批 |
| 试点数据集 | 无 | 接口 50 + Web 30 的资产清单与导入路径可复现（脚本 + 清单） | 本批（真实导入需环境） |
| 环境指纹可复现 | 模型已有 | 交付"按环境生成/比对指纹"的接线与可执行校验 | 本批 |
| 连续 3 版本 SLO | 无 | 演练脚本一条命令产出 3 个版本数字 + 验收报告模板 | 本批（真实跑需环境） |

## 4. 非目标（本次不做）

- **不新建证据体系**：`execution_evidence_store` 与 `EvidenceCompletenessPolicy` **收敛成一套判定**，不并存两套完整率口径。
- **不新建指纹/账号槽位/版本记录模型**：全部复用既有 `EnvironmentFingerprint` / `session_credentials_service` / `ExecutionCampaign` 系列。
- **不动老队列**（§4 硬约束 2）；**不做真机**（09 §0 D2）。
- **不伪造真实执行结果**：B4-3/4/5 的真实数字必须由环境产出（C 条件），本批只交付可跑通的演练与模板。

## 5. 用户故事 + 验收标准

- As a 版本负责人, I want 证据包被改过一个字节就能看出来, so that 放行结论所依赖的证据是可校验的。
  验收：Given 一个已落盘的证据包 / When 改动任一文件一字节 / Then 校验返回 `tampered` 并列出该文件；且该文件**不再满足**必需证据（完整率变为不完整）。

- As a 测试工程师, I want 知道这个证据包还缺什么, so that 我能补齐而不是猜。
  验收：Given API 任务少了 response / Web 任务少了 console / When 校验 / Then 返回缺失的必需证据类型清单。

- As a 试点负责人, I want 一条命令跑完 3 个版本并拿到数字, so that 我能在有环境的机器上复现 SLO。
  验收：Given 接 VPN 的机器 / When 执行演练脚本 / Then 输出 3 个版本的完整率、复用命中率与耗时，并生成验收报告骨架。

## 6. 交付切分与 C 条件

| 任务 | 本批交付 | 真实环境依赖 |
|------|---------|-------------|
| B4-1 | ✅ 校验服务 + API + 篡改显红前端 + 回归 | 无 |
| B4-2 | ✅ 数据集/基线制备脚本与清单 + 指纹/账号槽位接线 + 回归 | 真实导入与指纹采集需环境（C261-1） |
| B4-3/4/5 | ✅ 演练脚本（一条命令跑 3 版本）+ 验收报告模板 | 真实数字需 VPN + 体育资产（C261-1、C258-1、C260-1） |

## 7. 技能使用

- `cameltv-bug-guard` → 开工前核对"同一能力存两份"复发风险（本次重点：证据完整率口径、指纹模型），结论落在 §1 §4（非测试证据）。
- `cameltv-agent-team` → 批次档位与工件骨架（非测试证据）。
