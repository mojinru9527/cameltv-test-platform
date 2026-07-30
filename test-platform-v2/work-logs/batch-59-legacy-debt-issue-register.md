---
title: "Batch 59 — Batch 50–58 遗留问题收敛台账"
owner: "qa-team"
created: "2026-07-30"
last_reviewed: "2026-07-30"
status: "active"
expires: "2027-01-30"
tags: ["batch-59", "legacy-debt", "quality-gate", "acceptance"]
related:
  - "batch-57-j01-j22-atomic-evidence.md"
  - "batch-56-production-acceptance-issue-register.md"
  - "batch-59-legacy-debt-qa-report.md"
  - "../../C-CONDITIONS.md"
---

# Batch 59 — Batch 50–58 遗留问题收敛台账

## 1. 口径与结论

Batch 59 是遗留问题修复版，不新增业务模块。本台账以
`origin/main@5830622` 为基线，把 Batch 50–58 记录拆成：

- `FIXED-LOCAL`：本分支已修复且有本地可执行证据，合入前不写成生产关闭；
- `PARTIAL`：关闭了明确子缺口，但原条件仍有未执行范围；
- `READY-NOT-RUN`：自动化已补齐，但缺运行凭据或环境；
- `EXTERNAL-BLOCKED`：必须由外部服务、VPN、账号、设备或真实数据解除；
- `WAIVED`：风险已接受但不计作测试通过。

本批可确认的主要结果：

1. 质量门禁由“报告但放行”改为 fail-closed，并通过仓库契约测试。
2. 修复 Dataset 跨项目更新及参数化读取 IDOR。
3. 修复报告 CSV 崩溃和 Excel 空明细/错误统计。
4. 修复 AddCasesModal 旧筛选值请求、竞态与未取消请求。
5. React Hooks lint 暴露的 12 个问题已全部清零。
6. PostgreSQL 并发测试从永久 skip 改为 CI 必跑，并已在一次性 PostgreSQL 16
   数据库上完成迁移后 3/3 通过。
7. a11y 从假绿改为 Playwright 管理的确定性门禁，并修复 4 个 tablet Theme Lab
   WCAG 失败，最终 36/36 通过。

## 2. Batch 59 已修复并本地验证

| ID | 来源 | 状态 | 修复与证据 |
| --- | --- | --- | --- |
| B59-Q01 | Batch 58 CI 审计 | `FIXED-LOCAL` | ESLint 使用锁定依赖并覆盖 src/e2e/config 的 TypeScript、React Hooks、console/debugger 规则；135 条既有 unused 逐文件形成显式非回退基线；覆盖率以 Batch 58 实测基线为门槛；a11y、lint、coverage 均取消吞错 |
| B59-Q02 | Batch 48/57 PG skip | `FIXED-LOCAL` | required CI 启动 PostgreSQL 16、先 `alembic upgrade head`，再执行 3 个并发回归；本地一次性 PG 16 实跑 3/3 |
| B59-Q03 | Jenkins 遗留 | `FIXED-LOCAL` | 仓库 Jenkins 镜像升级 Node 22、流水线最低版本断言、F821、fail-fast、后端根构建上下文、首次随机并跨部署复用 secrets、Compose 解析和容器内后端健康检查 |
| B59-BE01 | J04/J19 | `FIXED-LOCAL` | Dataset update 与参数化执行读取均绑定 `project_id`；跨项目详情/更新/删除/行读取无泄露 |
| B59-BE02 | J10 | `FIXED-LOCAL` | CSV 改用文本缓冲后 UTF-8 BOM 输出；CSV/XLSX 转义公式前缀；报告快照补最新执行人/备注；Excel 映射 `cases/stats/plan_info` 的真实字段 |
| B59-FE01 | 前端审计 | `FIXED-LOCAL` | AddCasesModal 事件显式传递新 domain/module/keyword；旧请求中止；关闭/卸载清理；2 项 Vitest |
| B59-FE02 | 前端审计 | `FIXED-LOCAL` | 12 个 hooks 依赖/异步生命周期问题清零；`npm run lint` 退出码 0 |
| B59-FE03 | a11y 遗留 | `FIXED-LOCAL` | tablet 下 Theme Lab header 隐藏非关键 coverage 摘要，消除 4 个 WCAG 对比度/越界失败；全矩阵 36/36 |
| B59-FE04 | Agent Team 审查 | `FIXED-LOCAL` | WikiDiff 历史任务改为单一可取消请求/轮询，避免重复 GET 与旧响应覆盖；CaseDrawer 域列表延迟时保留原模块 |
| B59-TEST01 | Agent Team worktree | `FIXED-LOCAL` | 性能 WebSocket 测试不再硬编码 5173，改用当前 worktree CORS origin；独立端口下 38/38 |
| B59-MIG01 | Batch 57 warning | `FIXED-LOCAL` | Alembic `version_path_separator` 改为 `path_separator`；迁移回归 4/4，无该弃用告警 |
| G56-015 | Batch 56 | `CLOSED-WITH-NOTICE` | Batch 57 已归档前后端许可证清单和 psycopg2-binary NOTICE；从 Open 表移至 Closed |

## 3. G56-014 本批原子证据进展

| 旅程 | Batch 59 新增证据 | 当前判定 | 仍缺 |
| --- | --- | --- | --- |
| J02 Dashboard | 选中项目、空项目、跨项目聚合的 HTTP/返回值/DB count | `PARTIAL` | 低权限角色真实浏览器与全关联下游同源矩阵 |
| J04 Dataset/Integration | Dataset CRUD/坏 JSON/分页/IDOR；Integration secret mask/CRUD/IDOR | `PARTIAL` | 真实坏地址验证和六服务外部连通 |
| J10 Report | create/detail/list/CSV/Excel/delete、失败统计、foreign plan/report | `PARTIAL` | 报告模板坏输入、缺陷同源、真实浏览器 |
| J12 Defect | create、全状态链、history/stats、非法重试、跨项目、DB transition/audit | `PARTIAL` | 从真实 UI 失败执行创建缺陷的完整主链 |
| J17 Release bundle | parent/child CRUD、版本链、分页、跨项目 parent/detail/update/delete | `PARTIAL` | 详情/全景的需求→用例→执行→缺陷→报告同源聚合和重复发布 |
| J19 横向专项 | Dataset/Integration/Report/Defect/Bundle 的部分分页、count、IDOR | `PARTIAL` | 所有资源统一矩阵、并发/幂等和真实浏览器 |

`G56-014` 继续 `OPEN`。本批新增 8 项后端验收均通过，但不能用局部
HTTP/DB 测试替代 J01–J22 的全部真实 UI/API/DB 主链。

## 4. 仓库内仍可继续解决

| 范围 | 优先级 | 建议后续切片 |
| --- | --- | --- |
| J03 项目/用户/角色/Token 与撤权矩阵 | P0 | 独立 RBAC/API 批次，覆盖三身份和撤权后 IDOR |
| J08 用例/脑图导入、坏格式、重复、跨页 search/sort/count | P0 | 资产导入与分页专项 |
| J09 计划双击/并发、取消/重试、浏览器刷新持久化 | P0 | 生命周期浏览器专项 |
| J15 生成 TS→编译→真实 Playwright→Trace/report | P0 | runner 端到端专项 |
| J16 仓库内媒体 API schema 与正负面样本 | P1 | 不含真机/弱网部分 |
| J02/J04/J10/J12/J17/J19 的剩余列 | P0 | 在同源 fixture 上补 UI、schema 和业务副作用 |
| 后端扩展 Ruff/mypy/覆盖率 | P1 | 先建立可达基线，再分域提高，禁止一次性吞错 |

## 5. 已就绪但未完成真实运行

| ID | 状态 | 当前证据 | 缺口 |
| --- | --- | --- | --- |
| C55-5-P2 | `PARTIAL / READY-NOT-RUN` | fixture a11y 响应式矩阵 36/36；真实后端 E2E 已增加 tablet `768×1024` 与 mobile `390×844` 两项并成功收集 | 未提供 `E2E_USERNAME/E2E_PASSWORD`，未执行真实登录、全部 API、动态实体创建/清理 |

## 6. 外部阻断继续保留

| ID | 状态 | 解除条件摘要 |
| --- | --- | --- |
| B56-B01 | `FAIL / EXTERNAL-BLOCKED` | 测试节点 6 恢复后在同一授权网络复测 |
| B56-B02 | `FAIL / EXTERNAL-BLOCKED` | 六份实时 OpenAPI 或可追溯脱敏快照 |
| B56-B03 | `FAIL / EXTERNAL-BLOCKED` | 外部测试 API 鉴权实现与 OpenAPI 对齐 |
| B56-B04 | `FAIL / EXTERNAL-BLOCKED` | 运营后台真实浏览器会话修复后复测 |
| B56-B05 | `EXTERNAL-BLOCKED` | 真实 AI/OCR provider、授权 Key 和无 fallback 证据 |
| B56-B06 | `EXTERNAL-BLOCKED` | 认证设备代理、SoloX、真机和采样窗口 |
| B56-B07 | `EXTERNAL-BLOCKED` | ELK 只读入口、索引和脱敏 trace |
| B56-B08 | `WAIVED` | 未来取得旧 PostgreSQL 脱敏快照时补测；不是 PASS |
| B56-B09 | `PARTIAL / EXTERNAL-BLOCKED` | 运营后台设计源、版本、时间和 SHA |
| B56-B10 | `FAIL / EXTERNAL-BLOCKED` | 批准窗口和正确 VPN 边界内复测生产节点 |
| G56-011 | `OPEN / EXTERNAL-BLOCKED` | 真实设计源与真实 AI/OCR 的 J06/J07/J13 闭环 |

## 7. Batch 58 云条件真实性对账

2026-07-30 的匿名 HEAD 验证显示登记的 Vercel URL 返回 `302` 并跳转到
Vercel SSO，不是公开应用 HTTP 200。clean worktree 中不存在受 Git 忽略的
`production.env`，而 `vercel.json` 的后端 rewrite 仍指向
`backend.cameltv-platform.example.com` 占位域名。

因此 C58-01～06 均不能按当前仓库证据全部关闭：

- C58-01 `OPEN`：Cloudflare 原条件未完成；
- C58-02 `PARTIAL`：部署存在，但公开访问未通过；
- C58-03/C58-04 `UNVERIFIED`：缺可复现的非秘密连接/运行证据；
- C58-05 `PARTIAL`：文档回填不等于依赖条件可用；
- C58-06 `OPEN`：后端托管和 `/api` 真实目标未确定。
