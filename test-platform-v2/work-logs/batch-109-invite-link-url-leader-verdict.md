# Batch 109 — Leader Verdict（邀请链接正式域名 + 生产种子演示用户开关 + 生产启用收尾）

> **Leader (🎯)** | Date: 2026-08-06 | Decision: APPROVED（待用户一次总确认 + PR required checks 全绿后合入）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | 通过 | 两处生产缺陷均最小化修复：配置优先 + 默认兼容 |
| 风险 | 低 | 无迁移/无前端改动/无新依赖；未配置 `FRONTEND_URL` 时回退不破坏现有 |
| 覆盖 | 通过 | 18 模块测试 + 全量 1146 passed；两条新分支均有断言 |

## 关键决策（已批准）

1. **FRONTEND_URL 配置优先，空值回退请求域名**：生产配置
   `https://cameltv-test-platform1.vercel.app` 后邀请链接即指向正式前端；
   未配置环境（本地/testserver）行为与历史一致。
2. **SEED_DEMO_USERS 默认 true 保持兼容**：生产置 false 后不再重建 tester/viewer
   演示账号，角色本身保留；`validate_security` 联动豁免 TESTER_PASSWORD 必填。
3. **生产启用收尾**：C104-2/C105-2/C106-1 以生产实测证据关闭；验收数据清理仅保留
   admin/sportsadmin/admin1 + cameltv 项目，清理前快照已备份。

## 抽检通过

- ✅ `backend/app/api/v1/project.py` — `settings.frontend_url or req.base_url`（配置优先 + 回退）
- ✅ `backend/app/seed.py` — `seed_demo_users` 条件化 + 角色/成员关系守卫（tester_user/viewer_user None 安全）
- ✅ `backend/app/core/config.py` — 两个新字段 + `validate_security` 联动
- ✅ `backend/tests/test_project_invite.py::test_invite_url_uses_configured_frontend_url`
- ✅ `backend/tests/test_seed_credentials.py` 新增 2 用例
- ✅ 门禁：ruff F821 0 / import OK / Alembic 单头 / scan HARD 0（WARN 209 基线持平）/
  audit-cconditions 0 硬错 / pytest 1146 passed 3 skipped

## 判决

**APPROVED**。合入前置：① 用户一次总确认；② 首轮审计；③ required checks 全绿后最终审计。

## 下一批次 Leader 条件

- **C109-1**: 生产部署后配置 `FRONTEND_URL=https://cameltv-test-platform1.vercel.app` 与
  `SEED_DEMO_USERS=false`，复测项目邀请链接（https、页面 200、注册自动入项目/组织），
  并确认 tester/viewer 演示账号未重建。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 生产验收发现可分享链接用 `req.base_url` 拼 URL，反代后域名/协议失真 | 新增 `FRONTEND_URL` 配置优先 + 回退；QA 复盘卡增加「完整 URL 断言」 | config.py + project.py + evidence |
| 演示账号清理会被 seed 复活 | 新增 `SEED_DEMO_USERS` 开关并同步生产校验 | seed.py + env 模板 ×3 + checklist |
| 生产凭据与本地记录不一致 | 用户授权临时密码重置并登录验证；建议改密同步 | B109-3 + checklist §6 |
| Batch 107（#145）判决 C107-1/C107-2 未入追踪器（存量漂移，audit 报孤儿） | 本批补录到 C-CONDITIONS batch-107 节，audit 恢复 0 硬错 | C-CONDITIONS batch-107 节 |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 4h vs ≈3.5h | 0/1/1/1 | 0 | 技术债 + 外部依赖 | 可分享 URL 纳入生产验收断言；部署前置变量先核对 |

**技能使用**: `cameltv-agent-team` / `cameltv-bug-guard`；KB 以本地工件替代核查。
