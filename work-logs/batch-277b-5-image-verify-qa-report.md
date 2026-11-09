# Batch 277b-5 — QA Report

> **部门**：🔍 QA · **日期**：2026-11-09

| 项 | 结果 | 证据 |
|----|:----:|------|
| Dockerfile RUN 语法 | ✅ | `docker build` 成功（修复前 `Syntax error: "&&" unexpected`） |
| 镜像 ID/大小 | ✅ | `sha256:de4d963b…` / 811,859,174 B |
| 无 Chromium | ✅ | `command -v` 全空；`find` 无输出 |
| ENV | ✅ | `CONTROL_PLANE_BROWSER_ENABLED=false`、`UITEST_EXECUTION_MODE=node`、无 `PLAYWRIGHT_BROWSERS_PATH` |
| `/uitest` 节点 E2E | ✅ | 277b-3 已证（run done / 1/1） |
| 守卫 P0-4 | ✅ | `True … 控制面 Dockerfile 无浏览器安装` |
| 整守卫 | 🟡 | `FAIL (2/5: P0-1,P0-3)` 符合事实 |

## 风险 / 遗留

| 项 | 说明 |
|----|------|
| 生产 digest | 部署窗口重建后复核 |
| `start-worker.sh` 缺失（main） | Dockerfile 引用但 main 无此文件；本次构建临时补入，需单独确认归属 |
| P0-1 / P0-3 | Key 全 401；48h 水位观察中 |

## 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | 0.3 人日 / 实际 ≈ 50min（含构建与踩坑） |
| 缺陷 | 2（RUN 语法、main 缺文件） |
| 返工 | 2 |
| 根因 | Dockerfile 从未在 CI 构建；本地构建才暴露 |
