# Batch 101 — PRD（体育平台正式承接：生产环境接入）

> **Product (🟦)** | Date: 2026-08-06 | Status: Review

```markdown
mode: full
豁免理由: 无（新接入配置 + 生产环境写入，走完整六部门流水线）。
非目标: Test5 内网验收矩阵（S2）待 Test5 环境恢复（C95-1/C74-2）；iOS 双场景待 solox 支持（CP-C2/C84-1）；
运营后台登录链路（生产账号不公开）；旧数据迁移。
```

## 1. 问题陈述

按用户目标「在测试平台生产环境通过正常浏览器行为正式承接体育平台」：

- 将 7 个真实 Test5 契约导入平台 API 资产库（S1 契约对齐）；
- 在生产环境创建「体育平台-生产」环境与只读冒烟 UI 自动化任务（真实浏览器访问 www.camel1.tv，S3 起点）；
- 创建音视频专项任务（match replays，S4，真实 URL 待业务提供时补全）；
- 创建每日 API 回归定时任务与 CI 开放 Token；
- 一键可重复的接入脚本 + 生产执行证据。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| 契约导入 | 7 个真实契约文件落盘 | 全部导入平台 API 资产（服务+端点） |
| 生产只读冒烟 | 无 | UI 自动化任务可触发，真实浏览器访问 www.camel1.tv 通过 |
| 定时任务 | 无 | 每日 API 回归 schedule 创建并启用 |
| 开放 Token | 无 | CI Token 创建（token 仅本次回显，凭证不入库） |
| 接入脚本 | 无 | `scripts/sports/onboard-sports-platform.py` 可重复执行 |
| 证据 | 无 | 生产执行记录（契约导入数/UI run 状态/截图产物） |

## 3. 用户故事 + 验收标准

- As a **承接负责人**, I want 一键把体育平台契约/环境/冒烟/定时接入测试平台生产，so that 正式承接有据可查。
- As a **QA**, I want 生产只读浏览器 E2E 真实跑通，so that「正常浏览器行为」验收成立。

Given 接入脚本在生产执行成功，When 查询资产/任务/运行记录，Then 契约数、UI run 状态、计划与定时任务均可复核。

## 4. 技术考量

- 平台生产后端（Railway）镜像含 Playwright Chromium + ffmpeg，可执行 UI/音视频任务。
- 契约导入走 `/apitest/import/preview → confirm`（openapi_text，spec_content 内联）；confirm 时 `create_plan=true` 生成测试计划供 schedule 绑定。
- UI 冒烟用 `production-smoke.spec.ts` + 环境变量（PROD_ALLOWED_HOSTS / PROD_EXPECTED_BUSINESS_TEXT / PROD_SMOKE_OWNER / PROD_LOGIN_AUTHORIZED=false），只读不登录。
- 生产管理员凭据从 gitignored `production.env` 读取（不回显）；脚本创建独立 API Token 供 CI 使用。
