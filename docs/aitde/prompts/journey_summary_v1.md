# 观察旅程摘要（Observed Journey Summary）v1

> 关联方案：`docs/aitde/versions/V3.6_Detailed_Development_Implementation_Plan.md` §10 / §5（XHR Capture 改造）。
> 目标：把一条**已持久化、已脱敏**的生产旅程压缩为一页**可审计**、**只读**、**无密**的摘要，供评审与回放。

## 输入

- `ObservedJourney`：`name`、`journey_hash`、`summary_json`、`source_ref_json`。
- `steps[]`：`sequence`、`event_type`、`semantic_action`、`url_template`、`sanitized xhr_refs`。
  - `xhr_refs` 已脱敏：`headers` 中 `Authorization` / `Cookie` / `token` → `<REDACTED>`；`body` 已 sanitize。

## 任务

把旅程转成 **有序步骤** 的可读摘要，每步固定包含：

- `step`（序号，从 1 开始）
- `event_type`（`NAVIGATE` / `XHR` / `SEMANTIC` / `SCROLL`）
- `semantic_action`（人类可读，如 `view_news` / `click_pay`）
- `url_template`（已模板化 URL，不含敏感切面 / `Authorization` 参数）
- `read_only`（布尔，必须为 `true`；本旅程是只读观察）
- 对 `XHR` 步骤额外给出：`method` / `status` / `headers`（仅保留非敏感键与 `<REDACTED>` 占位）/ `body`（保持已脱敏字符串，**禁止还原**）

## 硬约束

- **摘要中禁止出现任何原始 `Authorization` / `Cookie` / `token` 值。** 出现即视为违规输出，必须重新生成。脱敏后的 `<REDACTED>` 可以直接出现。
- 不得还原 / 推断 `body` 中已被 `<REDACTED>` 的部分；不得输出真实用户 / 订单 / 凭据。
- 本旅程整体标注 **只读（read-only）**：仅观察，未发生任何生产写（无下单 / 支付 / 退款 / 建单等）。
- **不追加契约条文、不给出你作为评审者才该给的裁决**（PASS / FAIL 由 Required Oracle + Deterministic Assertion + Evidence 链路决定，AI 不拥有裁决权）。

## 输出格式

```text
Journey: <name>
hash: <journey_hash>
mode: OBSERVE | READONLY_EXPLORE
read_only: true

步骤：
1. [NAVIGATE]        打开 <url_template>
2. [SEMANTIC]        view_news   (read_only=true)
3. [XHR]             GET /news/... → 200  Authorization=<REDACTED>  Cookie=<REDACTED>  body=(sanitized)
...

关键点：
- 共 N 步，全部只读
- 观察到 1 个未在 contract_refs 中的语义动作：`view_news`（建议进入 Gap Analysis，人工确认）
```

## 自检

- [ ] 无任何 `Authorization` / `Cookie` / `token` 原始值
- [ ] 步骤按 `sequence` 升序、连续
- [ ] `read_only = true`
- [ ] 未把生产行为当作标准
