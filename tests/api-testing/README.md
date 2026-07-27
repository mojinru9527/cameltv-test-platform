---
title: "接口测试"
owner: "qa-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2026-12-26"
tags: ["api-testing", "postman", "bruno", "newman", "collections"]
related: ["tests/automation/README.md", "tests/README.md"]
---

# 接口测试

## 目录

```
api-testing/
├── collections/             # 接口请求集合（Postman / Bruno / Insomnia）
├── environments/            # 环境变量配置文件
└── reports/                 # 手工/半自动测试报告
```

## collections/ — 接口集合
按服务或模块拆分的请求集合，导出的 JSON 文件。建议使用 Bruno（基于文件的集合，便于 Git 管理）或 Postman Collection v2.1 格式。

## environments/ — 环境配置
每个目标环境一份配置：`dev`, `staging`, `prod`。包含 baseUrl、认证信息、公共 header 等。

## reports/ — 测试报告
使用集合运行器（如 Newman）生成的 HTML/JSON 报告，归属于具体的测试轮次。

> 可复用的接口自动化脚本应放入 [`../automation/service/`](../automation/service/)，本目录聚焦于手工/半自动场景。
