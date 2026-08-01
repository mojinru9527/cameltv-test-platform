# Batch 61 PC 使用快照索引

## 1. 规则

- 正常 PC 功能证据视口统一为 `1440×900`；长页可使用 full-page，但必须记录浏览器视口。
- `PASS` 图片必须来自真实成功状态，并有业务/API/数据/审计 oracle；路由外壳、加载、空态、错误页、Mock 或静态摆拍不计正常功能 `PASS`。
- 负面 fail-closed 可作为负面用例 `PASS`，但必须明确写“拒绝且零副作用”，不得冒充正常主流程截图。
- 每张图需在索引中记录快照 ID、功能点、动作、数据等级、环境、代码 SHA、执行人/日期和脱敏结果。
- Batch 60 的 `PC-B60-0001`～`PC-B60-0053` 原 ID 和证据路径保持不变，仅作历史基线；Batch 61 不重编号、不覆盖，也不自动继承 PASS。
- Batch 61 初始没有新截图，因此本文件没有任何 `PASS` 记录。

计划证据目录：

`work-logs/evidence/batch-61-production-readiness/pc-usage-snapshots/`

## 2. Batch 60 基线引用

| 范围 | 历史事实 | Batch 61 使用方式 |
| --- | --- | --- |
| PC-B60-0001～0053 | 51 张 PNG + 2 份 CSV，见 `batch-60-pc-usage-snapshot-index.md` | 仅用于修复前后对比；改动功能必须重新取证 |
| B60 正常子功能 | 多数为 PARTIAL PASS | 不得上卷为 Batch 61 模块 PASS |
| B60 阻塞/未执行功能 | Test5、通知、真机、外部集成、旧 PG、运维平台 | 保持阻塞/延期，不能以空态补图 |

## 3. Batch 61 计划快照

以下 ID 为预留索引；只有实际文件存在并完成视觉/敏感信息复核后才能改为 `PASS`。

| 快照 ID | 功能点 / 原始问题 | 应展示的实际动作与 oracle | 数据/环境 | 计划文件名 | Owner | 初始状态 |
| --- | --- | --- | --- | --- | --- | --- |
| PC-B61-0001 | FP-PROJ-001 / B60-P0-003 | 项目 A→B 后旧行清零；B 仅有效 GET；写操作使用 B 上下文 | R1、本地 A/B 项目 | `FP-PROJ-001-01-all-scoped-pages-switch-PASS.png` | Frontend owner / `UNASSIGNED` | `NOT RUN` |
| PC-B61-0002 | FP-API-001 / B60-P0-004、P1-019 | 五入口显示同一目标/环境/变量；production 无确认被服务端拒绝且零外呼/任务 | M 负面 + 本地安全端点 | `FP-API-001-01-five-entry-production-guard-PASS.png` | API owner / `UNASSIGNED` | `NOT RUN` |
| PC-B61-0003 | FP-CASE-001 / B60-P1-006 | 批量删除取消零请求；确认页显示数量、项目和不可逆提示 | R1、本地隔离数据 | `FP-CASE-001-01-bulk-delete-confirmation-PASS.png` | Frontend owner / `UNASSIGNED` | `NOT RUN` |
| PC-B61-0004 | FP-REL-001 / B60-P1-008 | 真实截图标注保存→重载→编辑，坐标/语义/API/DB 一致 | R1 发布包 | `FP-REL-001-01-interaction-reload-edit-PASS.png` | Frontend owner / `UNASSIGNED` | `NOT RUN` |
| PC-B61-0005 | FP-RBAC-001 / B60-P1-009 | tester/readonly 页面无未授权写入口；直接 API 仍拒绝 | 本地三身份 | `FP-RBAC-001-01-readonly-action-surface-PASS.png` | RBAC owner / `UNASSIGNED` | `NOT RUN` |
| PC-B61-0006 | FP-A11Y-001 / B60-P1-011 | 1440×900 目标页焦点、label/名称、键盘路径和无阻塞溢出 | 本地真实页面 | `FP-A11Y-001-01-desktop-keyboard-focus-PASS.png` | Accessibility owner / `UNASSIGNED` | `NOT RUN` |
| PC-B61-0007 | FP-AUTH-001 / B60-P1-020 | 重置账号首次登录被强制改密；完成后才进入业务路由 | 本地隔离账号 | `FP-AUTH-001-01-must-change-password-PASS.png` | Auth owner / `UNASSIGNED` | `NOT RUN` |
| PC-B61-0008 | SP-UI-HOME/LIST/DETAIL / B60-P1-012 | Test5 首页→列表→详情，DOM/API/业务数据一致且无静默 skip | R2 Test5 | `SP-UI-001-01-test5-readonly-journey-PASS.png` | Sports data/account owner / `UNASSIGNED` | `BLOCKED` |
| PC-B61-0009 | SP-UI-AUTH / B60-P0-001、P1-013 | 授权登录、会话可见元素、刷新续期和登出；截图/产物无凭据 | R2 Test5 | `SP-UI-002-01-test5-auth-session-PASS.png` | Test5 account owner / `UNASSIGNED` | `BLOCKED` |
| PC-B61-0010 | OPS0 | Jenkins/Runner 显示 release ID、前后端 digest、Alembic、SBOM/签名/QA 组成 | Test release | `OPS-001-01-release-composition-PASS.png` | DevOps owner / `UNASSIGNED` | `BLOCKED` |
| PC-B61-0011 | OPS1 | `TEST_VERIFIED` 时间线显示锁、备份、迁移、后端、前端、健康和 Smoke | Test release | `OPS-001-02-test-verified-timeline-PASS.png` | DevOps owner / `UNASSIGNED` | `BLOCKED` |
| PC-B61-0012 | OPS1 | 受控失败进入 fail-closed，随后应用回滚到上一兼容 release | Test release | `OPS-001-03-controlled-failure-rollback-PASS.png` | DevOps owner / `UNASSIGNED` | `BLOCKED` |
| PC-B61-0013 | OPS1 | 部署后真实体育测试平台版本/健康页与 manifest digest/revision 一致 | Test release | `OPS-001-04-platform-version-health-PASS.png` | DevOps owner / `UNASSIGNED` | `BLOCKED` |

## 4. 模块覆盖账本

| 模块组 | Batch 61 取证要求 | 初始状态 |
| --- | --- | --- |
| W1 被修改的生产保护、项目隔离、RBAC、改密、a11y、批删、标注 | 每个正常主流程至少一张 B61 新图；负面拒绝另列 oracle | `NOT RUN` |
| 未修改且已在 B60 通过的正常子功能 | 最终全平台回归后可引用 B60 历史图，但必须记录 B61 代码 SHA 和复核结果；不能复制成新图 | `NOT RUN` |
| W2 Test5 体育只读和授权登录 | 真实 R2 成功态；每条同时有 DOM/API/data oracle | `BLOCKED` |
| Test5 支付/退款/赠送 | 仅独立书面授权后截图；生产永不执行 | `BLOCKED` |
| W3 运维 release MVP | Batch 61 无产品化运维 UI；只取 Jenkins/Runner 与真实平台证据，不伪造控制台页面 | `BLOCKED` |
| OPS2 运维控制面 API/UI | Batch 62 范围 | `DEFERRED` |
| Production 发布/迁移 | Batch 62/63 且需独立授权 | `DEFERRED` |

## 5. 更新门禁

1. 文件存在、尺寸符合、视觉可读和敏感信息扫描通过后，才能从 `NOT RUN`/`BLOCKED` 改为 `PASS`。
2. 图片只证明可见状态；写操作仍需链接 API、DB/任务和审计证据。
3. 失败截图登记为 `FAIL` 证据，不得因“成功捕获缺陷”而把功能状态写成 `PASS`。
4. 最终图片数量必须与本索引、验收矩阵、问题台账和 release readiness 汇总一致。
