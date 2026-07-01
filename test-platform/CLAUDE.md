---
title: "test-platform — 测试平台 v1 旧版（维护模式）"
owner: "qa-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2027-06-26"
tags: ["test-platform", "v1", "legacy", "maintenance"]
related: ["../test-platform-v2/CLAUDE.md", "../docs/adr/0001-use-python-fastapi-monostack.md"]
---

# test-platform — 测试平台 v1（旧版单体）

> **状态：维护模式**。新功能开发已迁移到 `../test-platform-v2/`。v1 仅做 bug 修复和关键维护。

## 架构概览

```
test-platform/
├── cli/tp.py              统一 CLI 入口 `tp`
├── tools/                  10 件工具套件
├── server/                 FastAPI Web 后端
├── web-ui/                 React 18 + Ant Design 5 前端
├── core/                   核心组件 (配置/HTTP/日志/模型)
└── config/                 多站点多环境 YAML 配置
```

- **模式**：单体架构，CLI + Web 双入口
- **CLI**：`tp` 命令，支持 `--env test|prod` 多环境
- **Web**：FastAPI 后端 (8000) + React 前端 (5173)

## 10 件工具套件

| 工具 | 命令 | 目录 | 说明 |
|------|------|------|------|
| 环境探活 | `tp envcheck` | tools/env_check/ | 并发检查 DB/Redis/MQ/HTTP/版本 |
| API 测试 | `tp api` | tools/api_tester/ | Swagger 优先 + UI 捕获补充 |
| 流量抓取 | `tp capture` | tools/traffic_monitor/ | 基于 mitmproxy 录制真实请求 |
| Mock Server | `tp mock` | tools/mock_server/ | WireMock Docker 容器 |
| 双环境对比 | `tp apidiff` | tools/api_diff/ | JSON 逐字段比对 prod vs test |
| 数据工厂 | `tp datafactory` | tools/data_factory/ | YAML 驱动测试数据生成 |
| 日志聚合 | `tp logagg` | tools/log_aggregator/ | traceId 全链路日志 + ELK 链接 |
| 报告看板 | `tp report` | tools/report_dashboard/ | Streamlit 趋势看板 |
| 项目初始化 | `tp init-project` | tools/project_init/ | 交互式脚手架生成 |
| 音视频检测 | — | tools/av_checker/ | 音视频健康检查 |

## CLI 约定

- 所有需要环境的命令接受 `--env test|prod`
- 所有子命令通过 `tp <subcommand> --help` 获取帮助
- 凭据在 `test-platform/.env` 中配置

## 配置系统

`config/` 目录下的多站点多环境 YAML 配置：
- `_base/` — 基础配置
- `_template/` — 模板
- `environments/test.yaml` — 测试环境
- `environments/prod.yaml` — 生产环境
- `sites/` — 各站点覆盖

合并引擎：`core/config_loader.py`，支持 `_base` → `site` → `environment` 三级合并。

## 与 v2 的关系

- v1 的 CLI 工具套件仍在使用中，v2 暂未覆盖 CLI 场景
- v1 的 Web 端功能已被 v2 全面替代
- API 测试资产在 `tests/api-testing/` 下，两个版本共享
- **不要在 v1 中新增 Web 端功能**，新需求统一在 v2 实现

## 常用命令

见项目根 [COMMANDS.md](../COMMANDS.md) 第 2-5 节。
