# Batch 109 — PRD Summary（邀请链接正式域名 + 生产种子演示用户开关 + 生产启用回填）

> **Product (🟦)** | Date: 2026-08-06 | Status: Approved

## 0. 批次模式判定

`mode: full` — 引入新配置 `FRONTEND_URL` / `SEED_DEMO_USERS`（新配置），按完整批次执行六部门。

## 1. 问题陈述

1. **项目邀请链接打不开**（生产实测 2026-08-06，C106-1 上线验证发现）：
   `POST /projects/{id}/invites` 返回的链接是 `http://test-platform.up.railway.app/register?invite=...`，
   指向后端域名且协议丢失为 http，后端 `/register` 返回 404，同事拿到链接无法注册。
   正式前端 `https://cameltv-test-platform1.vercel.app/register` 已确认可达且支持 `?invite=` 参数。
   根因：`project.py:create_project_invite` 用 `req.base_url`（后端地址）拼链接，反代场景协议还退化成了 http。
2. **验收账号清理会被部署复活**（用户 2026-08-06 授权清理验收数据后核查）：
   `seed.run_seed()` 每次启动都会重建内置演示账号 tester/viewer 并重新加入默认项目，
   下次 Railway 部署后生产库清理将失效。需要一个生产开关控制是否创建内置演示账号。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 邀请链接域名 | 后端域名 + http + 404 | `FRONTEND_URL` 配置后为 https 正式前端域名且可打开 | 合入部署后复测 |
| 演示账号复活 | 每次部署重建 tester/viewer | `SEED_DEMO_USERS=false` 时不再重建 | 部署后重启一次核对 |
| 生产启用回填 | checklist/C-CONDITIONS 待回填 | §1/§2/§6 回填，C104-2/C105-2/C106-1 关闭 | 本批合入 |

## 3. 非目标（本次不做）

- 不改前端注册页/项目页（已支持 `?invite=` 参数，无需改动）
- 不做邮件通知、防刷/验证码（属 C106-2 灰度观察范围）
- 不删除 tester/viewer 角色本身（仅跳过演示账号创建）
- 不改变注册/邀请码/配额业务逻辑
- 不新增数据库迁移

## 4. 用户故事 + 验收标准

- **US-01** As a 项目负责人, I want 分享的邀请链接指向正式前端域名, so that 同事点开即可注册。
  - 验收：Given 生产配置 `FRONTEND_URL=https://cameltv-test-platform1.vercel.app` / When 负责人生成项目邀请链接 / Then 返回 `url` 以该域名开头（https），`/register?invite=` 页面可访问（200）。
  - 验收：Given `FRONTEND_URL` 未配置 / When 生成链接 / Then 回退请求域名（保持向后兼容）。
- **US-02** As a 平台运维, I want 生产不自动重建内置演示账号, so that 验收数据清理保持有效。
  - 验收：Given `SEED_DEMO_USERS=false` / When 启动执行 `run_seed()` / Then 不创建 tester/viewer 用户，也不创建其角色/项目成员关系；admin 与默认项目照常。
  - 验收：Given `SEED_DEMO_USERS=true`（默认） / When 启动 / Then 行为与历史完全一致。
- **US-03** As a 验收负责人, I want 生产启用清单与 C 条件回填, so that 交付可追溯。
  - 验收：Given 上线验证证据已产生 / When 本批合入 / Then checklist §1/§2/§6 回填完成，C104-2/C105-2/C106-1 关闭并带证据。

## 5. 技术考量

- 新配置项：`frontend_url`（`FRONTEND_URL`，空=回退请求域名）、`seed_demo_users`（`SEED_DEMO_USERS`，默认 true）。
- 生产安全校验联动：`seed_demo_users=true` 时继续要求 `TESTER_PASSWORD`；`false` 时豁免该校验。
- 风险与缓解：Railway 需人工新增两个变量（用户已确认可手动配置）；不配置 `FRONTEND_URL` 时行为回退，不破坏现有调用方。
- 依赖：无新第三方依赖、无迁移、无前端改动；测试覆盖种子开关与链接 URL 两条新分支。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main → Railway 自动部署 | 全部用户 | health 200，功能不回归 |
| 人工配置 `FRONTEND_URL` / `SEED_DEMO_USERS=false`（用户） | 运维 | 链接 https 200；重启后 tester/viewer 不出现 |
| 复测 checklist §4 #6 | 项目负责人 | 邀请链接注册自动入项目/组织 |

## 7. 技能使用

- `cameltv-agent-team` → 本批六部门流程与工件；
- `cameltv-bug-guard` → 后端配置/种子逻辑改动前避坑核对（本批不涉及新增路由/网络调用/前端副作用铁律）；
- KB 检索：本地 work-logs/PATTERNS 替代运行中知识库核查（与 Batch 106 口径一致）。
