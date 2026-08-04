# Batch 80 — Leader Verdict（C79-1 WARN 高价值项）

> **Leader (🎯)** | Date: 2026-08-04 | Decision: **APPROVED**（待用户 push 授权 + 二次确认 + CI checks 全绿后合入）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 需求聚焦 | PASS | 仅 C79-1 优先项（密钥 + 404 约定）；未扩范围 |
| 证据 | PASS | cipher 4 单测 + 本地全量 1027 passed；scan HARD=0 |
| 诚实性 | PASS | 首轮测试污染 146 ERROR 如实记录并修复；41 处 404 断言逐类核查后登记豁免 |
| 风险 | 低 | 密钥派生改动有全量回归兜底；API 行为不变 |

## 关键决策（已批准）

1. **固定回退密钥移除**：cipher 改用 `effective_secret_key`（dev 自动生成 / prod 缺失 RuntimeError），Batch 37 P1-01 关闭。
2. **404 双约定文档化**：隔离/守卫类 HTTP 404 正确；业务查不到用 200+code；scan 规则消息与判别表同步。
3. **测试隔离规范**：配置类单例一律注入隔离实例（monkeypatch 引用注入），禁止改全局单例。

## 抽检通过

- ✅ [cipher.py](test-platform-v2/backend/app/core/cipher.py) — 无固定回退；缺失即 RuntimeError
- ✅ [test_cipher.py](test-platform-v2/backend/tests/test_cipher.py) — 4 条单测 + 隔离注入
- ✅ [bug-guard](.claude/skills/cameltv-bug-guard/SKILL.md) — 404 双约定铁律
- ✅ scan 复扫 HARD=0 / cameltv-dev-key 0；本地全量 1027 passed

## 判决

**APPROVED**。可进入 push → Draft PR → 首轮 checks（后端全量回归必须 SUCCESS）→ 用户二次确认 → 合入流程。

## 下一批次 Leader 条件

- **C80-1（P2）**：剩余 WARN 230 项维持"分类 + 复核"管理——scripts print（运维脚本合法）、seed 一次性凭据、注释吞异常、404 双约定均已豁免/登记；后续新增代码不得引入新 WARN 类别；若发现业务"查不到"端点缺失 200+code 断言，修正测试。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| cipher.py 固定回退密钥（P1-01） | 改用 effective_secret_key + 单测 | cipher.py / test_cipher.py |
| 404 断言规则误报 41 处 | 双约定文档 + scan 消息细化 | bug-guard / scan-common-bugs.ps1 |
| 测试改全局单例污染后续测试（146 ERROR） | 隔离实例注入规范 | test_cipher.py / QA 复盘卡 |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 4h / 实际 3h | 0/1/0/1 | 1 | 测试污染 | 配置单例注入隔离实例；提交前全量回归 |

**技能使用**: `cameltv-agent-team` 完整批次；`cameltv-bug-guard`；`scan-common-bugs.ps1`。
