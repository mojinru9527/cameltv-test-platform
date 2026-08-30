---
name: test-data-masking-review
description: 用于 AITDE V3.6 脱敏（Masking）评审。Use when reviewing masking profiles/rules, or a masking validation report, to confirm no recoverable raw PII and that deterministic token/remap preserves relations. 脱敏输出有可恢复 PII 或关系被破坏 => INVALID。Triggers: "脱敏评审", "masking review", "数据脱敏", "脱敏规则复核", "mask validation review", "脱敏校验报告".
---

# 数据脱敏评审（Data Masking Review）

> AITDE V3.6 V36-007/008/010。脱敏的唯一目标是：**不可恢复的原始 PII 零残留 + 关系字段用确定性 token/remap 保持关联。** 任何一项被破坏即判 `INVALID`。

## 策略语义（必须遵守）

`MaskingStrategy`（`app.modules.aitde.common.enums`）：

| 策略 | 语义 | 是否保关系 |
|---|---|---|
| `REDACT` | 整值替换为 `<REDACTED>`，无条件安全 | 不适用（无值） |
| `HASH` | SHA-256；**不可逆**；同一明文 → 同一哈希 | 仅同一明文一致，跨不同明文不保业务关联 |
| `TOKENIZE` | 确定性 token（`tok_<sha256(salt:value)[:16]>`）；**同一 profile 盐下同一明文 → 同一 token** | **保关系**（用于 `user_id`/`order_id` 之类关系字段） |
| `FAKE` | 确定性伪值（`fake_<sha256(value)[:8]>`），外观仿真 | 确定性但需确认业务一致性 |
| `PRESERVE` | **原样保留** | 仅允许用于非敏感 / `classification=PRESERVE` 字段；对 PII 用 PRESERVE = 违规 |

## 评审流程

1. 取 masking profile + rules：`masking_profiles` / `masking_rules`（`entity_pattern` / `field_pattern` / `classification` / `strategy` / `config_json` / `priority`）。
2. 用 `PiiClassifier`（`app.modules.aitde.production.services.pii_classifier`）对每个字段做 `classify(field, value)`；确定哪些属于 `EMAIL` / `PHONE` / `PERSON_NAME` / `ID_NUMBER` / `ADDRESS` / `BANK_ACCOUNT` / `TOKEN` / `DEVICE_ID` / `IP`。
3. 应用规则得到 mask 输出，然后：
   - **PII 泄漏检查**：输出中不得存在与输入相同的原始敏感值（`MaskingService.validation_report` 的 `leaks`）；`leaks` 非空 → **INVALID**。
   - **关系保持检查**：同一 profile 下相同关系字段（如 `user_id` / `order_id`）必须映射到**相同** token/remap；`id_remap_json` 需证明映射确定。
4. Template 构建后（V36-010）再次确认：`template_json` 内**不含任何原始 PII**（字符串包含检查）。
5. 给出结论与依据：`VALID` 或 `INVALID` + 原因。

## 判定规则

- 一个 Mask Validation Report 出现任意 `leak`（可恢复原始 PII）→ **整个 `INVALID`**，不允许部分放行。
- 关键关系字段用了非确定性策略（可能导致关系不一致）→ `INVALID`（关系被破坏）。
- 对高敏感 PII（`EMAIL`/`PHONE`/`ID_NUMBER`/`TOKEN`/`ADDRESS`/`BANK_ACCOUNT`）采用 `PRESERVE` → `INVALID`。
- 全部满足 → `VALID`，可进入 Template Materialization（V36-011）。

## 提交前自检

- [ ] `validation_report.valid === true`（无 `leaks`）
- [ ] 关系字段 token/remap 确定性可复现
- [ ] 高敏感字段未被 `PRESERVE`
- [ ] 输出无原始 `Authorization` / `Cookie` / `token` / 身份证 / 手机号 / 邮箱
- [ ] 结论要么 `VALID` 要么 `INVALID`，给出依据；不给出「部分放行」
