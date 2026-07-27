---
title: "tests — 测试资产中心"
owner: "qa-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2026-12-26"
tags: ["testing", "test-cases", "automation", "api-testing", "av-testing"]
related: ["../test-platform-v2/CLAUDE.md", "test-case-standards/测试用例标准.md", "../lanhu-mcp/CLAUDE.md"]
---

# tests — 测试资产

> CamelTv 全链路测试资产中心：功能用例 + 接口测试 + UI 自动化 + 音视频专项。

## 目录结构

```
tests/
├── README.md                    测试体系总览与规范
├── requirements/                需求分析
│   ├── documents/               需求规格说明书 (PRD/FRD)
│   └── traceability-matrix/     需求-用例追溯矩阵
├── test-cases/
│   ├── functional/              功能测试用例 (ADMIN / BASELINE / P0-*)
│   ├── integration/             集成测试用例
│   ├── performance/             性能测试用例
│   └── security/                安全测试用例
├── api-testing/                 接口测试
│   ├── collections/             接口集合 (Postman/Bruno)
│   ├── environments/            环境变量
│   └── reports/                 测试报告
├── automation/
│   ├── ui/                      UI 自动化 (Playwright TypeScript, 6 模块)
│   ├── service/                 接口/服务层自动化
│   ├── fixtures/                测试数据与夹具
│   └── utils/                   公共工具模块
├── test-case-standards/         10 篇测试标准文档
├── 音视频测试/                  10 篇音视频测试指南
└── 音视频项目测试/              测试素材 + 分析脚本
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
| 需求文档 | `{系统}-{版本}-需求规格说明书.md` | `CamelTv-v1.0-需求规格说明书.md` |
| 接口集合 | `{服务名}-{环境}.json` | `user-service-dev.json` |
| 自动化脚本 | `test_{模块}.py` 或 `test_{module}.ts` | `test_login.py` |
| 测试数据 | `{实体}_{场景}.json` | `user_invalid.json` |

## UI 自动化模块

`automation/ui/` 下有 6 个模块的 Playwright (TypeScript) 规格文件：

| 模块 | 覆盖范围 |
|------|---------|
| home | 首页推荐 |
| list | 文章列表 |
| detail | 文章详情 |
| pay | 支付流程 |
| refund | 退款流程 |
| bonus | 奖励/Camel Coins |

P0 用例与 Playwright 规格文件之间有双向追溯关系。

## 自动化执行策略

| 触发条件 | 执行范围 |
|----------|---------|
| PR 提交 | Service 层自动化（必须通过） |
| 合并到 main | 全量回归 |
| 每日凌晨 (定时) | 冒烟套件 |

## 关联文档

- 总览：[README.md](README.md)
- 测试标准：[test-case-standards/](test-case-standards/)
- 自动化策略：[automation/README.md](automation/README.md)
- API 测试：[api-testing/README.md](api-testing/README.md)
- 音视频测试：[音视频测试/README.md](音视频测试/README.md)
