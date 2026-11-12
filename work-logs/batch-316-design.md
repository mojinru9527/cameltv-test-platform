# Batch 316 — Design / Dev

## 接口

```python
SportsVerticalAdapter(executor).run() -> {
  total, passed, failed, all_passed,
  results: [{case_id, title, passed, evidence, error}]
}
```

## 用例

TC-AIQE-001..010：入口、起播、暂停/恢复、清晰度、收藏、搜索、断流重连、比分、分享、弱网。

## 缺陷演示

执行器对 `TC-AIQE-007` 注入“重连超时” → 1 失败 + trace 证据；修复标志打开后 10/10。

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-316-1 | executor 注入 | 不绑定真实浏览器，先固化纵向契约 |
| D-316-2 | 汇总保留证据/错误 | 失败可定位 |
| D-316-3 | 固定 10 条 ID | 与验收编号一一对应 |

## 文件

- `app/aiqe/adapters/cameltv_sports.py`（+ `__init__.py`）
- `tests/test_aiqe_sports_vertical.py`（4 条）
