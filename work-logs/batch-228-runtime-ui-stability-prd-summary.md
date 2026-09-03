---
title: "Batch 228 Runtime 与任务页稳定性修复 PRD"
owner: "qa-team"
last_reviewed: "2026-09-03"
status: "approved"
expires: "2027-03-03"
tags: ["batch-228", "durable-runtime", "worker", "missions", "stability"]
---

# Batch 228 Runtime 与任务页稳定性修复 — PRD

> Product | Date: 2026-09-03 | Mode: full | Executor: Codex

## 1. 问题陈述

生产页面出现了三个会直接削弱用户判断和操作信心的问题：

1. 新业务接入同时显示“业务接入基线已就绪”和“耐久运行尚未就绪”，用户容易把可选的耐久执行能力误解为整个接入失败。
2. Durable Runtime 的 Worker 离线时操作列为空、能力列显示“无”，用户既不知道为什么离线，也没有可执行的重新检查入口。
3. 智能测试任务的“范围”和“场景”页把 `loading` 同时当加载状态和刷新触发器，加载结束会再次触发请求，形成持续闪烁和重复 GET。

代码审计同时确认：Worker 启动脚本只注册一次心跳，而控制面会在 180 秒后把失联心跳标为离线；Worker 列表接口又漏掉 capability 数据。即使 Worker 进程仍在运行，页面也会稳定复现“离线 + 能力无”。

## 2. 成功指标

| 指标 | 基线 | 本批目标 | 测量方式 |
|------|------|----------|----------|
| 范围/场景首屏请求 | 加载状态切换后无限重复 | 每次挂载 1 次；每次成功操作后仅刷新 1 次 | Vitest 请求次数断言 |
| 异步请求清理 | 创建了 AbortSignal 但未传给 API | 依赖变化/卸载可取消有效 GET | Vitest 参数与 AbortSignal 断言 |
| Worker 在线保持 | 启动时仅 1 次心跳，180 秒后离线 | 默认每 60 秒心跳；瞬时失败继续重试；退出时清理 | Pytest 心跳循环测试 |
| Worker 能力列表 | 列表固定显示“无” | 列表返回真实 capability，且使用单次批量查询 | Pytest 数据与查询数断言 |
| Runtime 离线可诊断性 | 操作列空白 | 显示恢复说明、最后心跳和“重新检查” | 组件测试 + 浏览器走查 |
| 接入状态理解 | 耐久未就绪看起来像接入失败 | 明示“不影响当前业务接入与同步基线” | 组件测试 + 三视口截图 |

## 3. 用户故事与验收标准

- As a 测试人员, I want 范围和场景数据稳定显示, so that 我能连续评审而不会被加载闪烁打断。
  - Given 打开范围或场景页 / When 首次数据加载完成 / Then 同一列表 GET 只发生一次且页面不重新进入 Skeleton。
  - Given 完成分析、生成或评审 / When 操作成功 / Then 列表只额外刷新一次。
- As a 平台管理员, I want Worker 状态真实且可诊断, so that 我能区分进程离线、网络中断和页面数据缺失。
  - Given Worker 进程持续运行 / When 超过 180 秒 / Then 默认 60 秒心跳使其保持在线。
  - Given 一次心跳网络失败 / When 后续网络恢复 / Then 心跳循环继续重试并恢复在线状态。
  - Given Worker 离线 / When 打开 Durable Runtime / Then 页面显示恢复说明和重新检查入口，不显示无意义的空操作列。
- As a 新业务接入用户, I want 知道耐久运行是否阻断当前操作, so that 我不会因为可选能力未启用而停止正常接入。
  - Given `baseline_ready=true` 且 `durable_ready=false` / When 查看自动检查 / Then 页面明确说明当前业务接入和同步基线不受影响。

## 4. 非目标与 C 条件

- 不在 Web 请求或前端按钮中启动、停止 Docker、Temporal Server 或远程 Worker 进程。
- 不把 `PROD_RO` 改成可写；它表示生产业务目标只读保护，与管理员管理 Worker 的权限不是同一概念。
- 不在本批直接部署或修改生产数据。代码合入、发布火车、生产部署和部署后验收是不同阶段。
- 不把本地自动化通过写成生产 Durable Runtime 已恢复；生产仍需管理员配置 Temporal、启动 Worker 并验证真实网络与凭据。
- C225-1 是 B1-B15 最终验收总项，本批不代替该专项。
- C227-1 是 Batch 227 的 PR 门禁，本批不篡改其历史状态。
- C227-2 仅部分承接 Worker 稳定性和说明；健康 AI、真实 OpenAPI/被测地址及生产部署仍按原解除条件保留 Deferred。

## 5. 技术考量

- 前端遵循 `useAbortableEffect` 约定：加载状态不进入依赖数组，刷新使用独立递增版本号，所有 GET 传递 signal。
- Worker capability 由后端一次批量查询组装，禁止对列表逐行查询。
- 心跳循环放入可单测的 Python 模块，由现有 `start-worker.sh` 与 Temporal Worker 同生命周期启动；默认 60 秒，小于控制面 180 秒失联阈值。
- 心跳失败只记录并按间隔重试，不把瞬时 Control Plane 故障升级成 Worker 进程崩溃；进程退出时停止循环。

## 6. 上线计划

| 阶段 | 范围 | 成功门槛 |
|------|------|----------|
| 本地开发 | 前后端与 Worker 生命周期 | 定向测试、双端硬门禁、脚本检查全部通过 |
| Draft PR | main required checks | 用户总确认后推送；检查全绿并通过最终审计 |
| 发布火车 | test 后生产 | Runtime 真实心跳连续超过 180 秒、页面在线、任务页无重复 GET |

## 7. 技能使用

- `cameltv-agent-team`：确定完整批次、六部门工件、QA 与 Git 门禁。
- `cameltv-bug-guard`：将异步 cleanup、重复请求和 N+1 查询列为阻断项。
- `cameltv-ui-conventions`：离线态采用清晰说明、语义色和可触达刷新入口。
- `vision`：识别用户截图中的状态组合、空操作列和页面闪烁上下文。
- 知识库 MCP 在当前会话不可用；替代核查了 `C-CONDITIONS.md`、Batch 227 工件、`docs/common-pitfalls.md` 与相邻测试模式。
