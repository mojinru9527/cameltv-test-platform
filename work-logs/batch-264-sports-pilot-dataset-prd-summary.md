# Batch 264 PRD-lite — 体育试点数据集（接口 50 + Web 30）

> **Product/PM** | Date: 2026-09-19 | 档位：**轻量批次**
> `mode: light`
> 豁免理由：产出**数据与工具**（试点用例集 + 落地脚本），不改平台运行时行为、不动 Schema/接口/依赖；判定见 `docs/agent-team/pipeline-modes.md`。

## 1. 背景与目标

§5 第 ⑦ 条（体育连续 3 版本 SLO）与第 ③ 条（8 条试点用例真机外跑通）都依赖 **B4-2 的试点数据集**（09 §2.3：接口 50 + Web 30）。
本批负责把这个数据集**真实造出来**（不允许写死清单、不允许凑数）。

## 2. 已核实的现状（命令与输出见 QA 报告）

| 环节 | 现状 | 证据 |
|---|---|---|
| 接口半边 | **本地可产出 50 条** | 仓库内 `camel-service.openapi.json`（197 接口）→ 导入 `created_count=197` → 模板生成 `591` 条 `case_type='api'` → 选择器 `api 50/50`（shortfall 0） |
| Web 半边 | **目标可达，用例待写** | Test5 篮球 UI `https://camel-bball-test5.elelive.cn/basketball` → 200；足球/直播 UI `https://camelive-g3-test5.elelive.cn` → 200；导航/标题已实测（`evidence/batch-264/test5-web-recon-20260919.json`） |
| 被测入口口径 | 网关按 `/<service>/` 路由 | 体育 API 基址 = `http://camel-api-gateway05.svc.elelive.cn/camel-service`（裸路径 404、带前缀 200） |
| 数据库口径 | `case_type`: api / manual / ui | `TestCase` 模型；选择器取 `case_type='api'` 50 条 + `case_type='ui'` 30 条，`module LIKE '<prefix>%'` |

## 3. 本批交付

1. **30 条体育 Web（`case_type='ui'`）用例**：基于上表实测页面（Home / News / My / 联赛入口 / Football↔Basketball 切换 / 赛程·比分·直播入口等）编写步骤与期望，模块统一前缀（默认 `体育/`）。
2. **试点集落地脚本**：一键完成「导入契约 → 生成 50 条接口用例 → 写入 30 条 Web 用例 → 用 `pilot_dataset_service` 自检」，输出 `50/50 + 30/30` 与基线快照。
3. **前置环境说明**：把「网关服务前缀」「Test5 UI 入口」「账号槽位（仅槽位名，不含凭据）」写进脚本参数与文档，供 ③/⑦ 直接复用。

## 4. 非目标

- ❌ 不改平台代码、不动 Schema、不加依赖
- ❌ 不写入任何被测系统凭据（只引用账号槽位名，符合 09 §3.1 / H3）
- ❌ 不把 manual 功能用例改名冒充 `ui` 用例（Batch 已裁定：那是贴标签，不是造数据）
- ❌ 不针对生产站点（`www.camel1.tv`）执行用例

## 5. 验收判据

| # | 判据 |
|---|------|
| A1 | `python scripts/build_pilot_baseline.py --module-prefix <前缀>` → `api shortfall 0` 且 `web shortfall 0`，`meets_target=true` |
| A2 | 30 条 Web 用例的步骤/期望来自真实页面（附页面实测证据），非模板套话 |
| A3 | 用例集中不含任何凭据；账号只以槽位名出现 |
| A4 | 门禁：`scan-common-bugs` HARD 0、`audit-cconditions` 0/0、CI 分类为文档/工具域 |
