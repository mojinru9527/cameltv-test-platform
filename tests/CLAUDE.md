---
title: "tests — 测试资产中心"
owner: "qa-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2026-12-26"
tags: ["testing", "test-cases", "test-case-standards"]
related: ["../test-platform-v2/CLAUDE.md", "test-case-standards/测试用例标准.md"]
---

# tests — 测试资产中心

> 通用测试资产中心：平台自身验收用例 + 测试标准。业务系统用例由使用方按标准自行沉淀。

## 目录结构

```
tests/
├── README.md                    测试资产中心总览与规范
├── test-cases/
│   ├── functional/              功能测试用例（平台自身验收资产）
│   ├── integration/             集成测试用例
│   ├── performance/             性能测试用例
│   └── security/                安全测试用例
└── test-case-standards/         通用测试标准文档
```

## 测试标准

所有测试用例必须遵循 [test-case-standards/](test-case-standards/) 下的规范：

- 用例模板：前置条件 + 步骤 + 预期结果 + 优先级
- 优先级体系：**P0**（核心，每版本必测）→ **P1**（常用）→ **P2**（一般）→ **P3**（次要）
- 功能用例和接口用例各自有对应的 checklist

## 命名规范

| 类型 | 格式 | 示例 |
|------|------|------|
| 测试用例 | `TC-{模块}-{编号}.md` | `TC-login-001.md` |
| 需求文档 | `{系统}-{版本}-需求规格说明书.md` | `demo-v1.0-需求规格说明书.md` |
| 接口集合 | `{服务名}-{环境}.json` | `user-service-dev.json` |
| 自动化脚本 | `test_{模块}.py` 或 `test_{module}.ts` | `test_login.py` |
| 测试数据 | `{实体}_{场景}.json` | `user_invalid.json` |

## 关联文档

- 总览：[README.md](README.md)
- 测试标准：[test-case-standards/](test-case-standards/)
- 测试平台：[../test-platform-v2/CLAUDE.md](../test-platform-v2/CLAUDE.md)
