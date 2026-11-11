# Batch 297（M3 / TA-020.3）— Oracle 来源守卫 CI：PRD-lite

> **部门**：🟦 Product（lite） · **日期**：2026-11-11
> **批次模式**：**light**（CI 守卫 + 内部流程工具；PRD-lite + QA + Leader + 看板）
> **分支**：feature/batch-297-m3-oracle-layer-guard · **基线**：origin/main `d8563b4e4`

## 1. 问题

13 号 §9.4 要求每条 assertion 显式声明 `oracle_layer`（REQ/STD/PATTERN），否则“页面正常/操作成功”
这类空预期会混入用例。此前只有文档约束，没有 CI 拦截。

## 2. 范围

- `scripts/ci/check-oracle-layer.ps1`：
  - 扫描 PR 变更的 `.json/.md` 文件（Markdown 内 ```json 代码块）；
  - 递归查找 `assertions` 数组，逐条要求 `oracle_layer ∈ {REQ,STD,PATTERN}`；
  - `-SelfTest` 内置正反样例；`-All` 可全量扫描；
- 接入 `ai-delivery-policy.yml`（先 self-test，再按 base 分支 diff 扫描）。

## 3. 成功指标

| 指标 | 阈值 | 结果 |
|------|------|:----:|
| 缺字段被拒 | exit 1 | ✅ |
| 非法枚举被拒 | exit 1 | ✅ |
| 合法 JSON/Markdown 通过 | exit 0 | ✅ |
| 只扫变更文件（不误伤历史） | 0 误报 | ✅ |
| self-test | PASS | ✅ |

## 4. 非目标

- 不校验 `oracle_ref` 是否真实存在（后续与用例库联调）；
- 不改历史文档中的旧 assertion（仅约束新增/修改）。
