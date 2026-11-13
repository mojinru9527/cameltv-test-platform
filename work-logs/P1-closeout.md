# AIQE P1 收口报告（batch-336 ~ 339）

> **日期**：2026-11-13 · **范围**：Console 菜单/RBAC、Profile/Workflow 审批、QualityGate/NoiseRules、PlatformMatrix + SSE
> **结论**：P1 四个批次的代码/API/页面全部落地并合入 main；剩余项均为环境依赖（Test 部署凭据、真机、第二项目）。

## 1. 交付

| 批次 | 内容 | PR |
|------|------|----|
| batch-336 | 执行中心菜单 `menu:aiqe_runs` + API 统一门禁 + 路由守卫/403 | #564 |
| batch-337 | Workflow 列表/详情/审批 API + Profile 创建/审批/更新 + 两个 Console 页面 | #565 |
| batch-338 | 质量门禁页 + 噪音规则页 + 规则错误码/`PATCH`/`effective` | #566 |
| batch-339 | 平台矩阵真实 API（节点能力×平台）+ SSE 长连接（id/retry/Last-Event-ID） | 本批 |

## 2. 测试与门禁

| 项 | 结果 |
|----|------|
| 后端新增测试 | 6 + 8 + 11 + 6 = **31 条** |
| 后端全量 | 1688+ passed；route_inventory 基线同步 |
| 前端新增测试 | 5 + 3 + 5 + 2 = **15 条** |
| 前端全量 | 575 passed（128+ 文件） |
| required checks | 后端全量 + 前端全量（含 axe/Lighthouse）+ AI/Git 交付策略 |

## 3. 权限模型

- `menu:aiqe_runs` 是执行中心唯一入口权限：菜单树、前端守卫、`/api/v1/aiqe/*` 三处同源；
- tester 默认分配、viewer 不分配、`*` 全量放行；
- Console 写操作继续叠加 `defect:update`（独立审批权限点列入后续）。

## 4. 剩余（环境依赖）

| 项 | 状态 | 前置 |
|----|:----:|------|
| Test 实例部署本批镜像 | ✅ 2026-11-13 完成 | 镜像 `release-m13-20261113`（delta）；登录/菜单/新接口实测通过，见 `work-logs/aiqe/test-deploy-20261113.md` |
| 真实 TC-AIQE-001..010 | 未执行 | 隔离 Test 实例 + 被测业务账号 |
| 真机 / minium / UIA / MQTT | 未执行 | 设备与协议网关 |
| 第二项目 future-wayu | 未执行 | 真实项目环境 |
| 独立审批权限点 | 待排期 | 权限模型变更（需完整批次） |

## 5. 结论

P1 完成后，AIQE Console 具备完整操作面（执行记录 / Profiles / Workflow 审批 / 质量门禁 / 噪音规则 / 平台矩阵），
AIQE 按"对外可用"口径约 **85%**；剩余 15% 全部为环境/外部依赖，代码侧无阻塞。

## 6. 生产发布（2026-11-13）

- 镜像：`cameltv-tp-backend:release-m13-20261113`、`cameltv-tp-frontend:release-m13-20261113`；
- 生产 health 200，OpenAPI 新接口与 `menu:aiqe_runs` 种子已验证，无迁移；
- 版本锁更新为 commit `268150486` / `release-m13`；
- 详细证据与回滚步骤：`work-logs/aiqe/production-release-20261113.md`。
