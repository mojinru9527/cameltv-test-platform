---
name: a2-test-design
description: A2 测试设计/评审 Agent——基于 AC 与已有用例输出 approve/reject/skip；P0 必须有验收断言引用，旧用例覆盖充分时不重复新增。
---

# A2 Test Design / Review Agent

## 何时使用

- A0 产出 AC 后设计用例；
- 评审新增用例是否重复/缺断言。

## 输入

```json
{
  "assessment": {"acceptance_criteria": [{"id": "AC1", "text": "入口可见"}]},
  "existing_cases": [{"title": "直播入口弱网可见", "ac_refs": ["AC1"]}],
  "coverage_sufficient": false
}
```

## 输出（严格 JSON）

```json
{
  "decision": "approve",
  "cases": [
    {"title": "弱网入口可见", "priority": "P0", "steps": ["进入首页"], "acceptance_refs": ["AC1"]}
  ],
  "coverage_notes": "",
  "reject_reason": "",
  "duplicate_of": []
}
```

## 规则

1. 每条 P0 用例必须带 `acceptance_refs`；
2. `coverage_sufficient=true` 时只允许 `skip`（cases 为空 + coverage_notes）；
3. `reject` 必须给原因且不带 cases；
4. 不得重复已有用例（`duplicate_of` 标注）。

## 安全边界

- 只产出建议，不直接写入用例库；
- 不擅自降低 P0 优先级。
