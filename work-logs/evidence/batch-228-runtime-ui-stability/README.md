# Batch 228 Runtime 与任务页稳定性证据索引

> Date: 2026-09-04 | Branch: `fix/batch-228-runtime-ui-stability` | Base: `origin/main@7a9c4adc`

## 环境边界

- 浏览器环境：隔离 worktree；Scope/Scenario/onboarding 使用本地前端 `127.0.0.1:5198`、后端 `127.0.0.1:8028`，最终 Runtime 增量复验使用一次性前端 `127.0.0.1:5199`、后端 `127.0.0.1:8029` 和独立临时库。
- Runtime 走查临时启用本地 `AITDE_V3_ENABLED=true`，并创建一条过期心跳的 `TEST` Worker 测试记录；临时库与浏览器会话在取证后删除。
- 范围/场景走查通过页面创建本地 Mission `M-1-0001`，只用于请求次数与响应式验证。
- 本证据不访问、不修改生产数据，也不代表生产 Temporal 或 Worker 已恢复。

## 证据索引

| 证据 ID | 覆盖范围 | 类型 | 基线或增量 | 对应提交 | 结论 | 复用规则 |
|---------|----------|------|------------|----------|------|----------|
| E228-01 | 新业务接入状态口径 | 3 视口截图 | 本批增量 | `936e605c` | PASS | onboarding 状态组件未改时可复用 |
| E228-02 | Runtime 离线恢复态、真实能力与本地时区 | 3 视口截图 | 本批增量 | `936e605c/a78a37db` | PASS | Worker 表格、列表或时间契约未改时可复用 |
| E228-03 | 范围 Tab 稳定加载 | 3 视口截图 | 本批增量 | `936e605c` | PASS | Scope effect/API 未改时可复用 |
| E228-04 | 场景 Tab 稳定加载 | 3 视口截图 | 本批增量 | `936e605c` | PASS | Scenario effect/API 未改时可复用 |
| E228-05 | Scope/Scenario/Runtime 请求次数与管理员状态 | 浏览器 Network | 本批增量 | `936e605c..a78a37db` | PASS | 对应 effect、状态或时间契约未改时可复用 |
| E228-06 | 双端自动化与生产构建 | 回归结果 | 本批增量 | `a78a37db` | PASS | 后续变更命中对应域后失效 |
| E228-07 | G0-G2、迁移与 C 条件 | 门禁结果 | 本批增量 | `936e605c` | PASS_WITH_WARN | 每批重新执行 |

## 截图清单

`pc-usage-snapshots/` 包含以下每页 3 个视口：

- onboarding：`1440x900`、`768x1024`、`390x844`
- runtime：`1440x900`、`768x1024`、`390x844`
- scope：`1440x900`、`768x1024`、`390x844`
- scenarios：`1440x900`、`768x1024`、`390x844`

截图显示：文字和操作未互相覆盖；窄屏表格保留既有横向滚动容器；页面级导航与主要操作均在可见布局内。

## 关联结果

- 自动化与门禁：`regression/test-results.md`
- 浏览器请求证据：`regression/browser-network.md`
