# Batch 327（M8 / TA-043+044+045）— Domain Packs：PRD

> **模式**：完整 · **分支**：feature/batch-327-m8-domain-packs · **基线**：`100a1ad57`

## 目标

1. E-commerce Pack（future-wayu）：角色/实体/支付/退款/库存检查；
2. SaaS Pack：Tenant/RBAC/Audit 必备检查；
3. IoT Pack：Device shadow / telemetry / alert；
4. `list_packs/get_pack/validate_pack/apply_pack`，缺必备检查显式拒绝。

## 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 3 Pack 注册 | `test_three_packs_registered` |
| A2 | 查询/未知 | `test_get_pack_and_unknown` |
| A3 | 全 Pack 合法 | `test_all_packs_valid` |
| A4 | SaaS RBAC/Audit | `test_saas_requires_tenant_rbac_audit` |
| A5 | IoT shadow/telemetry | `test_iot_shadow_and_telemetry` |
| A6 | apply 形状 | `test_apply_pack_shape` |
| A7 | 缺检查拒绝 | `test_missing_checks_rejected` |
| A8 | 全量 | pytest + ratchet |

## 非目标

- 真实 future-wayu 项目接入（Pack 契约先固化）。
