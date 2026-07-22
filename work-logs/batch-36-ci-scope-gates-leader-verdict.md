---
title: "Batch 36 CI 按变更范围分层 Leader 判决"
owner: "leader"
last_reviewed: "2026-07-23"
status: "pending"
tags: ["leader", "ci", "github-actions"]
---

# 当前判决

`PENDING`。以下条件全部满足前不得批准：

1. 分类矩阵、CLI 与 workflow 静态契约测试通过；
2. 三个 ruleset required context 名称不变；
3. Draft PR 首轮检查通过，CI workflow 变更按保守规则执行双端全量；
4. 用户第二次确认实际执行器为 Codex 并授权最终交付；
5. 最终审计确认 required checks 成功且 PR 可合并。

本地抽检阶段结果为 `PASS`：10 项分类/契约测试、YAML 解析、Git 治理自测和 ruleset API 均通过，且没有测试平台业务文件进入变更。Leader 最终批准仍被真实 PR 证据与用户二次确认阻塞。

# 抽检重点

- 顶层 path filter 不能导致 required workflow 消失。
- detector 失败不能因 dependent job 被 skipped 而假绿。
- 未识别路径必须双端执行，不能用维护成本换取漏测风险。
