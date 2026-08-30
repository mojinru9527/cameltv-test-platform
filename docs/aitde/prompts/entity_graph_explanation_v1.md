# 实体图说明（Entity Graph Explanation）v1

> 关联方案：`docs/aitde/versions/V3.6_Detailed_Development_Implementation_Plan.md` §10 / §4（EntityGraphExtractor）。
> 目标：把一张实体关系图用**测试人员能懂的白话**解释清楚——根实体、深度、关系类型——并**保证脱敏**。

## 输入

- `root`：`<entity_type>:<ref_hash>`
- `nodes[]`：`entity_type`、`ref_hash`（哈希 / token）、`depth`、可选 `attributes`（已脱敏）
- `edges[]`：`from`、`to`、`relation`（如 `FK` / `HAS_MANY` / `BELONGS_TO`）

## 任务

按以下结构输出：

1. **根实体**：`root` 是谁，代表什么业务主语（如订单 / 用户 / 会员）。
2. **拓扑层级**：用 `depth` 说明——`depth 0` 是根，`depth 1` 是直接子实体，`depth 2` 依此递推。
3. **关系说明**：逐边说明 `from → to` 经 `relation` 如何关联（`FK` 外键、`HAS_MANY` 一对多、`BELONGS_TO` 多对一等）。
4. **数据规模**：节点 / 边总数；是否触发过 `max_depth` / `max_nodes` 截断（若截断，说明该图**不完整**）。

## 硬约束

- **不得暴露任何原始 PII**：所有 `ref_hash` 已是哈希 / token，直接引用即可；`attributes` 若含敏感值必须已为 `<REDACTED>`。**禁止把哈希反推**成真实主键 / 身份证 / 手机号 / 邮箱。
- 用「实体类型 + 脱敏引用」描述，不要给出可还原真实主体的信息。
- 只做解释；**不要**据此自动修改 Contract / 场景 / 权限，**不要**触发任何写操作。
- 关系说明以 `edges` 中的 `relation` 字段为准；不要臆造图里没有的边。

## 输出格式

```text
根实体：order（ref_hash=…）
深度分布：
  depth 0：order
  depth 1：user, order_item
  depth 2：user_profile, payment
关系：
  order(FK)            → user          订单关联下单用户
  order(HAS_MANY)      → order_item    一个订单含多个明细
  user(BELONGS_TO)     → user_profile  用户拥有一个资料
说明：节点共 N，边共 M；未触发深度/节点上限（或：已触发上限，图被截断）。
```

## 自检

- [ ] 无原始 PII / 可还原引用
- [ ] 根 / 深度 / 关系解释来自输入字段
- [ ] 无任何 Contract / 权限 / 写操作桥接
