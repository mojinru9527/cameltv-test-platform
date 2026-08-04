# Batch 80 — PRD Summary（C79-1 WARN 高价值项）

> **Product (🟦)** | Date: 2026-08-04 | Status: Approved

## 1. 问题陈述

C79-1 要求优先消化两类 WARN：

1. **硬编码回退密钥（Batch 37 P1-01 仍在）**：`app/core/cipher.py` 在 `SECRET_KEY` 未配置时回退到固定密钥 `cameltv-dev-key`——攻击者拿到代码即可解密密文；且该路径绕过了 `effective_secret_key` 的开发自动生成机制。
2. **HTTP 404 断言规则过宽**：scan 对测试中所有 `status_code == 404` 报 WARN（41 处），但仓库存在**双 404 约定**——隔离/权限/存在性守卫走 HTTP 404（正确，防泄露），业务"查不到"走 HTTP 200 + body `code==404`；规则未区分导致大量误报。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量 |
|------|------|------|------|
| cameltv-dev-key | 1 处（cipher.py） | 0 | scan 复扫 |
| cipher 单测 | 无 | 4 条（roundtrip/dev/生产缺失报错/无回退） | pytest |
| 404 双约定 | 无文档 | bug-guard 规则 + scan 消息 | 结构检查 |
| scan HARD | 0 | 0 | scan 复扫 |
| 本地全量 pytest | 1023 | ≥1023 全绿 | pytest |

## 3. 非目标（本次不做）

- **不改 41 处 404 测试**：经逐类核查，隔离/守卫类断言 HTTP 404 是正确契约（豁免理由已写入 bug-guard 与 QA）。
- **不处理其余 WARN 类别**（scripts print、seed 一次性凭据、注释吞异常）：均为合理/有意，登记豁免。
- **不处理 C74-1/2/3**（外部依赖验收项）：继续豁免。

## 4. 用户故事 + 验收标准

- As 安全审计, I want 无固定密钥回退, so that 泄露密钥不构成解密能力。
  - 验收：Given 生产环境未配 SECRET_KEY / When 调用 encrypt / Then RuntimeError；开发环境自动生成会话密钥且 roundtrip 可用。
- As 测试作者, I want 404 约定清晰, so that 隔离守卫与业务查不到不被混淆。
  - 验收：Given bug-guard 文档 / When 阅读 / Then 双约定与判别方法明确；scan WARN 消息提示复核方向。

## 5. 技术考量

- cipher 改用 `settings.effective_secret_key`（dev 自动生成、prod 缺失即报错），与 `validate_security` 模型一致。
- 测试注入隔离 Settings 实例（monkeypatch cipher.settings），**禁止改全局单例**（Batch 80 首轮因改全局单例污染后续测试，教训已入流程回写）。
