# Batch 115 — PRD（体育平台 Part 2 全部解决）

> **Product (🟦)** | Date: 2026-08-07 | Status: Review

```markdown
mode: full
豁免理由: 无（含后端模型/Schema/调度/执行链路改动 + 前端入口 + 知识导入 + Runner 稳定性，走完整六部门流水线）。
非目标:
- Test5 契约补拉（C111-4 外部 Deferred）
- iOS 真机采集（CP-C2 外部：solox 缺 iOS 26.5）
- internal-network runner 启动（C111-1 外部）
- news/get 服务端代码修复（B112-1 属体育平台服务端，本批做口径确认/重探，不在本平台改）
```

## 1. 问题陈述

用户要求把「体育平台承接相关待解决项（第二部分）」全部解决，共 7 项：

1. **C107-1（P1）**：`tests/test-case-standards/接口测试考虑点【辅助作用】.md` 未导入生产知识中心。
2. **B112-3（P2）**：平台 `/schedules` 仅支持 plan 绑定，UI job 无法定时 → 每日 UI 回归只能手动/CI 触发。
3. **C107-2（P2）**：接口用例无「依赖接口/前置接口」配置，场景模板停留在「待关联」，无法真实多接口串联。
4. **B10/C103-5（P3/P1）**：无「页面 XHR 批量采集」平台工具；batch-112 校准暴露样本缺请求头。
5. **B114-2（P2）**：Railway 数据中心 Playwright Runner 不稳定（页面崩溃/OOM，run 10-13 波动）。
6. **B112-1（P1）**：news/get 生产全 id 业务 400 → 本批重探 + 用户口径确认（内部端点 or 服务端缺陷）。
7. **用户方向剩余**：用例生成链路未消费知识中心关联基座（生成前不自动按模块-接口-功能关联定位）。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| C107-1 | 考虑点文档未入库 | capture code=0 + sources 可见 + 检索命中 |
| B112-3 | UI job 无定时 | UiTestJob 支持 cron 定时 + schedule 服务 job_type=ui；平台创建定时任务并验证触发 |
| C107-2 | 无依赖配置 | TestCase 支持 depends_on_ids/前置接口配置；执行链先跑前置并把响应注入后置；场景串联用例实跑通过 |
| B10 | 无采集工具 | 平台 XHR 采集任务（只读 Playwright 采集指定页面 XHR 含请求头）产出样本 JSON + 证据 |
| B114-2 | run 10-13 波动 | chromium 启动参数加固 + 连续 2 次平台 10/10 |
| B112-1 | 业务 400 | 重探 + 口径确认 → 关闭或外部 Deferred 登记 |
| 生成链路 | 不消费基座 | 功能/接口生成提示注入关联基座检索结果（模块→接口→功能），单测验证 |

## 3. 用户故事 + 验收标准

- As a **QA**, I want UI 自动化每日定时回归（B112-3），so that 关键路径持续受控。
  - Given UI job 配置 cron，When 创建定时任务并触发，Then 运行报告 10/10。
- As a **接口测试工程师**, I want 用例可配置前置/依赖接口，so that 场景用例真实多接口串联。
  - Given 接口用例配置 depends_on，When 执行，Then 前置先跑、响应变量注入后置请求、断言通过。
- As a **承接负责人**, I want 页面 XHR 批量采集工具，so that 用例基线用真实请求/响应+请求头（C103-3/4）。
  - Given 采集任务指定页面列表，When 执行，Then 产出含 method/url/请求头/body/响应 的样本 JSON。
- As a **用例生成者**, I want 生成前自动按关联基座定位，so that 用例不遗漏模块/接口（用户方向闭环）。
  - Given 生成请求指定模块，When 生成，Then 提示词注入关联基座检索结果，单测断言包含模块-接口映射。

## 4. 技术考量

- **B112-3**：UiTestJob 增加 `cron_expression`/`schedule_enabled`；schedule 服务支持 `job_type`（plan|ui）+ `job_id`；
  APScheduler 触发 UI job（复用 `ui_test_service.trigger_job`）；迁移 + 单测 + 前端 UI job 管理页定时设置。
- **C107-2**：TestCase 增加 `depends_on_ids`（JSON 数组）与前置配置；执行器执行前置用例（同环境）并把
  `last_response_json` 解析为 `$prev.{case_key}.{jsonpath}` 变量注入后置 body/url；执行顺序拓扑 + 环检测。
- **B10**：复用 UiTestJob 新增「采集任务」（playwright 只读 capture）：拦截 response + request headers，
  批量页面 → 样本 JSON 落库/导出；仅 GET/查询型 POST（复用 B112-4 只读口径）。
- **B114-2**：playwright_executor chromium launch args 加 `--disable-dev-shm-usage --no-sandbox --disable-gpu`；
  spec retries=1 保留；连续 2 次平台 10/10 证据。
- **C107-1**：复用 capture 通道导入考虑点文档。
- **B112-1**：重探 news/get；与用户确认口径。
- **生成链路**：`case_generation_service`/`api_case_generation_service` 提示词注入知识检索
  （RAG query=模块名）结果中的接口/功能清单；单测断言注入。

## 5. 范围

**纳入**：7 项全部（后端模型/迁移/调度/执行链/采集/提示注入 + 前端 UI job 定时入口 + 知识导入 + Runner 加固 + 证据）。

**非目标**（见头部）。

## 6. 上线计划

| 阶段 | 内容 | 出口标准 |
|------|------|---------|
| S1 | 工件 + C107-1 知识导入 + B114-2 Runner 加固 | capture 证据 + 平台 10/10 连续 2 次 |
| S2 | B112-3 UI job 定时（模型/迁移/调度/前端/单测） | 单测 + 平台定时任务触发 10/10 |
| S3 | C107-2 接口依赖（模型/执行链/单测）+ 场景串联用例 | 单测 + 实跑 |
| S4 | B10 XHR 采集工具 + 生成链路消费基座 | 采集证据 + 单测 |
| S5 | B112-1 重探/口径 + QA/Leader + 一次总确认 | 工件齐全 + 审计 0 硬错 |

## 7. 技能使用

- `cameltv-agent-team` → 六部门流水线
- `cameltv-bug-guard` → 后端迁移/网络/断言避坑
- `playwright-cli`/`playwright-skill` → XHR 采集与 UI 定时验证
- `test-case-design` → 场景串联用例