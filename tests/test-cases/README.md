---
title: "测试用例"
owner: "qa-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2026-12-26"
tags: ["test-cases", "functional", "integration", "performance", "security", "template"]
related: ["tests/requirements/README.md", "tests/test-case-standards/"]
---

# 测试用例

## 目录

```
test-cases/
├── functional/              # 功能测试用例
├── integration/             # 集成测试用例
├── performance/             # 性能测试用例
└── security/                # 安全测试用例
```

## 用例编写模板

```markdown
# TC-{模块}-{编号}

| 字段       | 内容           |
| ---------- | -------------- |
| **用例ID** | TC-{模块}-{编号} |
| **关联需求** | REQ-xxx        |
| **优先级** | P0 / P1 / P2 / P3 |
| **前置条件** |                |
| **测试步骤** | 1. ... 2. ...  |
| **预期结果** |                |
| **实际结果** | (执行后填写)    |
| **执行人** |                |
| **执行日期** |                |
```

## 优先级图示

| 优先级 | 含义                     | 测试策略           |
| ------ | ------------------------ | ------------------ |
| P0     | 核心路径，阻塞性问题      | 每个版本必测       |
| P1     | 常用功能，严重影响使用    | 每个版本必测       |
| P2     | 一般功能，边界/异常       | 回归阶段覆盖       |
| P3     | 次要功能，UI/文案        | 时间充裕时覆盖     |
