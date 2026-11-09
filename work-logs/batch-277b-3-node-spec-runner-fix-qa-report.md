# Batch 277b-3 — QA Report

> **部门**：🔍 QA · **日期**：2026-11-09

## 1. 验收

| 项 | 结果 | 证据 |
|----|:----:|------|
| 真实 Chromium 执行 spec | ✅ | `1/1 pass`；report.json 解析出 1 条 passed |
| 本地 `/uitest` 全链路 | ✅ | `UiTestRun.status=done`、`result.passed=1`、`evidence_files=3`、`artifact_dir=.../job-1/attempt-1` |
| 产物 API | ✅ | 4 个文件（manifest/report/results/.last-run） |
| 单测 | ✅ | 12/12 |
| 仓库清洁 | ✅ | 单测 spec 写 tmp，仓库无残留 |
| quality ratchet | ✅ | increased_keys=0 |
| spec 安全 | ✅ | 控制面 `spec_guard` 拦截；节点相对路径白名单 |

## 2. 风险/遗留

| 项 | 说明 |
|----|------|
| 控制面 Dockerfile 仍装 Chromium | P0-4 未闭环，需处理 lanhu/xhr/playground |
| 真实生产节点 | 仅本机节点验证 |
| 默认模式 | 仍 local，生产零变化 |

## 3. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | 0.3 人日 / 实际 ≈ 40min |
| 缺陷 | 4（路径/命名/编码/项目参数） |
| 返工 | 3 |
| 根因 | 未在真实 Playwright 下验证 277b-1（单测 fake runner 掩盖环境差异） |
| 下次避免 | 新执行链路必须至少跑一次真实 CLI 冒烟 |

## 4. 判定

修复与 E2E 证据通过；P0-4 整体仍未闭环。
