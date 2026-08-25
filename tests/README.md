---
title: "测试资产中心"
owner: "qa-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2026-12-26"
tags: ["testing", "test-cases", "test-case-standards", "qa"]
related: ["tests/CLAUDE.md", "test-platform-v2/README.md"]
---

# 测试资产中心

## 目录结构

```
tests/
├── README.md                          # 本文件 — 测试资产中心总览与规范
├── test-cases/                        # 测试用例
│   ├── functional/                    # 功能测试用例（平台自身验收资产）
│   ├── integration/                   # 集成测试用例
│   ├── performance/                   # 性能测试用例
│   └── security/                      # 安全测试用例
└── test-case-standards/               # 通用测试标准（用例模板、优先级、检查点）
```

## 模块职责

### test-cases/ — 测试用例
按类型划分：功能、集成、性能、安全。用例采用统一模板（ID、前置条件、步骤、预期结果、优先级）。
当前保留平台自身验收资产（BATCH47/48/55 需求服务生产级验收/复测、batch-63 全功能点正负面矩阵），
业务系统用例由使用方按 `test-case-standards/` 标准自行沉淀。

### test-case-standards/ — 测试标准
通用测试规范与模板：功能/接口用例规范、检查点、生产级模块验收规则、缺陷管理制度等。
所有测试用例必须遵循该目录下的标准。

## 命名规范

| 类型       | 格式                                        | 示例                                     |
| ---------- | ------------------------------------------- | ---------------------------------------- |
| 测试用例   | `TC-{模块}-{编号}.md`                       | `TC-login-001.md`                        |
| 需求文档   | `{系统}-{版本}-需求规格说明书.md`           | `demo-v1.0-需求规格说明书.md`            |
| 接口集合   | `{服务名}-{环境}.json`                      | `user-service-dev.json`                  |
| 自动化脚本 | `test_{模块}.py` / `test_{module}.ts`       | `test_login.py`                          |
| 测试数据   | `{实体}_{场景}.json`                        | `user_invalid.json`                      |

## 用例优先级

- **P0** — 核心路径，阻塞性问题，每个版本必测
- **P1** — 常用功能，严重影响用户使用
- **P2** — 一般功能，边界/异常场景
- **P3** — 次要功能，UI/文案类
