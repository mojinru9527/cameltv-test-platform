---
title: "B1-B15 代码实现说明"
owner: "qa-team"
last_reviewed: "2026-09-03"
status: "active"
expires: "2027-03-03"
tags: ["platform-refactor", "b1-b15", "architecture", "implementation"]
related:
  - "docs/platform-refactor/07-b1-b15-delivery-and-usage.md"
  - "work-logs/evidence/batch-226-sports-v16-ai-e2e/b1-b15-matrix.json"
---

# B1-B15 代码实现说明

## 主链路与事实源

`VersionTask` 是版本验收的单一事实源，关联 requirement、plan items、runs/executions、defects、release bundle、coverage、risk 和 verdict。B14 收敛接口对外声明 `single_fact_source=version_task`，旧 TestPlan 只做历史归档，不参与读取双写。

```text
Requirement
  -> VersionTask
     -> AI PlanItem review
     -> Runner execution + evidence
     -> Defect draft/sync
     -> Release package + verdict
     -> Version knowledge
        -> reuse suggestions / regression set / comparison / metrics
```

## AI 方案

VersionTask 方案生成通过统一 `ai_client` 和项目级 AI 配置，提示上下文包含需求正文、变更模块及最多 200 个已导入 OpenAPI endpoint。JSON 输出只有限重试两次；空内容、非法 JSON 或无有效条目均返回业务错误。

AITDE 的 Scope、Contract、Scenario 仍支持确定性降级，目的是让人工流程可继续检查；降级不等于 AI 成功。Contract 的 `rules=[]`、Scenario 的 `items=[]` 均记为 AI Operation FAILED。

## 执行与放行门禁

Runner 只执行含 `exec_meta` 的条目。缺目标计入 `blocked`，不能计为 pass 或可忽略 skip。运行状态按以下优先级计算：空方案/blocked→blocked，failed→failed，存在真实 pass 且无其他问题→done，否则 blocked。

放行有两层保护：前端 `isPassVerdictAllowed` 禁用不合法操作；后端 `release_task` 再校验 pass>0 且 fail/skip/blocked 全为 0。release package 使用实际检查总数，0 checks 的通过率固定为 0%。

## 缺陷、知识与指标

缺陷草稿使用 VersionTask 的真实 `project_id`；前端仅在创建成功取得 `defect_id` 后允许同步。知识记录保存实际 verdict 和 coverage。复用建议、推荐回归、版本对比和运营指标均读取存储数据；没有录入回归人天时返回 `regression_person_days_recorded=false`，不再用任务数推算。

## B15 接入

BusinessOnboarding 强制按 1→2→3→4 推进：

1. 登记业务名、service key、OpenAPI URL、base URL。
2. 单次读取 JSON/YAML OpenAPI，预览并导入 endpoint，创建关联 VersionTask。
3. 用 OpenAPI endpoint 和需求上下文生成方案，并纳入向导执行状态。
4. 调 VersionTask Runner，持久化 status/pass/fail/skip/blocked；仅 `run.status=done` 时设为 active，否则 blocked。

## 前端副作用与接口契约

Source、Fragment、Ambiguity、Intent 列表接口的响应模型与实际 list 数据一致。Source/Contract 页面不再把 `loading` 作为 effect 触发条件，而用独立 `reloadVersion`；GET 透传 AbortSignal，组件卸载或参数变化时取消旧请求。VersionTask 与 Onboarding 的初始加载同样有取消保护和可见错误态。

## 已知运行边界

- OpenAPI URL 当前只支持单次 HTTP(S) JSON/YAML 读取；目标必须从本地验收环境可访问。
- AITDE 异步执行依赖 Temporal Worker；API 服务在线不代表 Worker 在线。
- AI Provider 的 HTTP 成功不代表语义成功，必须同时满足 JSON schema 和非空业务内容。
- 体育 16.0.0 本轮仍缺上述真实执行条件，因此实现可合入评审，但业务链路状态保持 BLOCKED。
