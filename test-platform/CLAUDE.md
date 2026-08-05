---
title: "test-platform — 测试平台 v1 旧版（维护模式）"
owner: "qa-team"
last_reviewed: "2026-08-05"
status: "active"
expires: "2027-02-05"
tags: ["test-platform", "v1", "legacy", "maintenance"]
related: ["../test-platform-v2/CLAUDE.md", "../docs/adr/0001-use-python-fastapi-monostack.md"]
---

# test-platform — 测试平台 v1（旧版单体）

> **状态：维护模式**。新功能开发已迁移到 `../test-platform-v2/`。v1 仅做 bug 修复和关键维护。

## 架构概览

```
test-platform/
├── cli/tp.py              统一 CLI 入口 `tp`
├── tools/                  11 件工具套件（Batch 98 已删除）
├── server/                 FastAPI Web 后端
├── web-ui/                 React 18 + Ant Design 5 前端
├── core/                   核心组件 (配置/HTTP/日志/模型)
└── config/                 多站点多环境 YAML 配置
```

- **模式**：单体架构，CLI + Web 双入口
- **CLI**：`tp` 命令，支持 `--env test|prod` 多环境
- **Web**：FastAPI 后端 (8000) + React 前端 (5173)

## 工具套件（Batch 98 已删除）

> **2026-08-05（Batch 98）**：11 个 V1 工具（环境探活 / API 测试 / 流量抓取 / Mock / 双环境对比 /
> 数据工厂 / 日志聚合 / 报告看板 / 项目初始化 / 音视频检测 / 压测）已按 C64-1 批准废弃并删除。
> CLI 仅保留 `config show/sites` 自检；CI 回归迁移至 `scripts/ci/api-regression.ps1` + Playwright 直跑。

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

- v1 的 CLI 工具套件已于 Batch 98 删除；CI 迁移至 `scripts/ci/api-regression.ps1`
- v1 的 Web 端功能已被 v2 全面替代
- API 测试资产在 `tests/api-testing/` 下，两个版本共享
- **不要在 v1 中新增 Web 端功能**，新需求统一在 v2 实现

## 常用命令

见项目根 [COMMANDS.md](../COMMANDS.md) 第 2-5 节。
