---
title: "Batch 56 真实客户输入清单"
owner: "qa-team"
created: "2026-07-29"
status: "active"
tags: ["batch-56", "real-input", "production-acceptance", "redacted"]
related:
  - "../../docs/测试平台全功能验收文档-环境链接与账号汇总.md"
  - "../../tests/test-case-standards/生产级模块验收规则.md"
  - "../../docs/superpowers/plans/2026-07-29-batch-56-full-platform-production-acceptance.md"
---

# Batch 56 真实客户输入清单

## 输入等级

| 等级 | 定义 | 可否关闭生产主流程门禁 |
|---|---|---|
| R0 | 用户授权的实时环境、实时需求页面、实时 OpenAPI 或实际客户文档 | 可以 |
| R1 | 从 R0/客户资料形成的脱敏、来源可追溯固定快照，记录 SHA-256 | 可以；外部实时连通性仍单独验收 |
| R2 | 严格依据 R0/R1 schema、业务规则与边界生成的数据 | 仅补充分页、并发、边界和异常 |
| M | Mock、stub、route fulfill、monkeypatch 或虚构 fixture | 仅证明受控回归分支，不计生产通过 |

每个 P0/P1 主流程至少绑定一项 R0 或 R1。只有 R2/M 时，用例状态只能是 `BLOCKED`、`NOT RUN` 或模拟回归结果。

## 固定 R1 输入

| 输入 ID | 来源 | 字节 | SHA-256 | 业务用途 | 脱敏/读写说明 |
|---|---|---:|---|---|---|
| B56-R1-ENV | `docs/测试平台全功能验收文档-环境链接与账号汇总.md` | 28836 | `23986b0d00e28750d10a6e100f4cc618d830fae8bec2f2d6a4999b7194a53549` | 环境、公开账号名、凭证槽位、资源索引和外部操作边界 | 不含实际凭据；只读取环境变量名 |
| B56-R1-PRD-FULL | `test-platform-v2/docs/CamelTv测试平台-完整PRD.md` | 21229 | `cefc99292ab1b92563368e82ae0449057affa443ac895323456eb5b3169b2ddf` | 测试平台模块、业务闭环与验收期望 | 仓库固定快照 |
| B56-R1-PRD-ASIS | `test-platform-v2/docs/现状功能PRD.md` | 23528 | `ce46bf066183459601dd4283802f602aba1faca69e65096f218a4477879147e2` | 现状能力与宣称事实核对 | 仓库固定快照 |
| B56-R1-PRD-API | `test-platform-v2/docs/接口测试模块优化PRD.md` | 15307 | `71f4f2fb8d238620202923603e258f2be6495a683c492ed2ca7bdafda8cfe0ce` | API 资产、调试、任务、快照、取消与生产保护 | 仓库固定快照 |
| B56-R1-USER-REQ | `tests/requirements/documents/用户端原型-需求分析.md` | 19430 | `0ac601bc19a01c456bf42638473548ceeb277f8b33e74f7c28d68028b465ca02` | 用户端真实业务术语、需求导入、用例与追溯 | 仓库脱敏需求分析 |
| B56-R1-ADMIN-REQ | `tests/requirements/documents/运营后台-需求分析.md` | 31062 | `e1282cc4fa3b0bf7c199254c28aa29231ab7dbad90fef597be492d9e04b02e59` | 运营后台真实业务术语、状态流与权限 | 仓库脱敏需求分析 |
| B56-R1-TRACE | `tests/requirements/traceability-matrix/matrix-v14.csv` | 12668 | `59abbf7bbd5ac6ecd0034938bb04363e46764a0e3598a0b5e324abdaec59e4de` | 需求—用例—自动化追溯与覆盖率输入 | 仓库固定矩阵 |
| B56-R1-USER-CASES | `tests/test-cases/functional/BASELINE-用户端-基线功能.md` | 60224 | `6fa83d83db899fb1e4757f5c5ca691aac797581b76bea6737d938f2764f6b11e` | 用户端生产形态用例、搜索词、边界和异常输入 | 仓库固定用例 |
| B56-R1-ADMIN-CASES | `tests/test-cases/functional/ADMIN-运营后台-全版本.md` | 97965 | `9459497f0b589c37154c42da97ed6c66cb9ba5612b422fb60d94dd050a8df232` | 后台模块、RBAC、审核与状态迁移输入 | 仓库固定用例 |
| B56-R1-OPENAPI | `test-platform/tests/api-testing/specs/cameltv-openapi.yaml` | 4285 | `79ad14de7d7afaeac21cf0f7981194f6cb54e3cc38702c1a48c7de1a319d3883` | API 资产导入、契约解析、环境对比与调试输入 | 仅读取 v1 固定 spec；不在其目录写入 |

## 待执行 R0 输入

| 输入 ID | 来源类别 | 允许操作 | 当前状态 | 阻塞/失效条件 |
|---|---|---|---|---|
| B56-R0-PROD-SITES | 体育平台生产镜像 | GET/HEAD、页面导航、公开内容与运行时检查 | NOT RUN | 网络/VPN/安全策略 |
| B56-R0-TEST-SITES | 体育平台测试节点 | 真实登录与只读浏览；写入需明确授权和可恢复数据 | NOT RUN | 内网、凭证或写权限缺失 |
| B56-R0-TEST-OPENAPI | 测试环境 Swagger/OpenAPI | GET 并与 R1 spec 比较 | NOT RUN | 内网不可达 |
| B56-R0-ADMIN-TEST | 运营后台测试环境 | 按文档登录规则进行只读核对 | NOT RUN | 内网不可达或共享状态风险 |
| B56-R0-USER-DESIGN | 用户端需求/设计源 | 只读提取、对照和脱敏截图 | NOT RUN | 蓝湖地址或合法凭据缺失 |
| B56-R0-ADMIN-DESIGN | 运营后台需求/设计源 | 只读提取、对照和脱敏截图 | NOT RUN | 蓝湖地址或合法凭据缺失 |
| B56-R0-AI | 配置的真实 AI 服务 | 需求拆分、生成、反向评审 | NOT RUN | `AI_API_KEY` 缺失或服务不可达 |
| B56-R0-ELK | ELK/Kibana | 只读 trace 和日志关联 | NOT RUN | VPN/凭据/索引权限缺失 |
| B56-R0-LEGACY-PG | 脱敏真实旧 PostgreSQL 快照 | 隔离克隆升级和只读前后核对 | NOT RUN | 快照或验收连接缺失 |

## R2 与 M 使用边界

- R2 仅从上述 R1 字段、枚举、长度、关系和状态机派生，用于 101+ 分页、并发、重复、错误字符、超限附件和跨项目数据。
- R2 数据统一使用 `B56-<时间戳>-<模块>-<用途>` 前缀，经 UI/公开 API 创建，并在 `finally` 清理。
- M 仅用于不可稳定制造的超时、断网、5xx、限流、坏附件、通知失败和 loading/empty/error UI。
- 报告必须分别统计 R0/R1 与 R2/M。任何 Mock 拦截点都要记录其不能证明的范围。
- 仓库和证据不得保存密码、Token、Cookie、Authorization、真实个人信息、完整敏感查询参数或原始生产正文。
