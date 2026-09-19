# Dev Kanban — Batch 264 体育试点数据集

> Batch: 264 | 模式: 轻量 | Scope: `docs,work-logs,C-CONDITIONS.md`

| # | 任务 | Product | PM | Dev | QA | Leader |
|---|------|:-------:|:--:|:---:|:--:|:------:|
| 1 | 目标侧实测取材（Test5 API + Web 可达性、导航/标题） | ✅ | ✅ | ✅ | ✅ | ✅ |
| 2 | 导入契约 → 生成 50 条接口用例（本地实测 591 条→选 50） | ✅ | ✅ | ✅ | ✅ | ✅ |
| 3 | 编写 30 条体育 Web 用例（基于真实页面） | ✅ | ✅ | ⏳ | ⏳ | ⏳ |
| 4 | 试点集落地脚本 + `build_pilot_baseline` 自检 50/50 + 30/30 | ✅ | ✅ | ⏳ | ⏳ | ⏳ |
| 5 | 门禁与工件 | — | — | ⏳ | ⏳ | ⏳ |

## 关键事实（供后续批次直接引用）

- 体育 API 入口：`http://camel-api-gateway05.svc.elelive.cn/camel-service`（裸路径 404，必须带服务前缀）。
- 体育 UI 入口：`https://camel-bball-test5.elelive.cn/basketball`（篮球）、`https://camelive-g3-test5.elelive.cn`（足球/直播）。
- 选择器口径：`case_type='api'` 取 50 + `case_type='ui'` 取 30，`module LIKE '<prefix>%'`，按 P0→P3 排序。
