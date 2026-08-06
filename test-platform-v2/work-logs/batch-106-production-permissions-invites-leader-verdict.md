# Batch 106 — Leader Verdict（生产启用 + 组织权限映射 + 项目邀请链接）

> **Leader (🎯)** | Date: 2026-08-06 | Decision: APPROVED（待用户一次总确认 + PR required checks 全绿后合入）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | 通过 | 三模块闭环：14 新测试 + 全量 1133 通过 |
| 风险 | 低-中 | 生产切换未自动执行（人工步骤 C106-1），代码合入无风险 |
| 覆盖 | 通过 | US-01~04 全过；越权/失效 token/迁移幂等均有断言 |

## 关键决策（已批准）

1. **组织权限映射**：组织负责人/管理员在组织内项目获得项目管理员能力（project:manage/
   update/delete/detail），普通组织成员保持只读访问；超管全量不变。
2. **项目邀请链接**：有效 token 免除平台邀请码；注册事务内自动加入项目与所属组织
   （原子化）；token 32 字节 secrets 随机，列表脱敏。
3. **生产启用**：本批完成清单与演练证据；实际生产切换（备份 → Railway 变量 →
   Supabase 迁移 → 验证）登记为 C106-1 人工步骤，用户确认执行窗口后回填清单。

## 抽检通过

- ✅ `backend/app/services/rbac_service.py` — org 推导权限仅按项目维度追加，不扩大全局；
- ✅ `backend/app/services/project_invite_service.py` — token 校验/消耗/脱敏；
- ✅ `backend/app/services/auth_service.py` — 项目 token 豁免 + 项目/组织自动加入；
- ✅ `backend/alembic/.../20260806_batch106_project_invite.py` — 单头（修复 merge 父节点）；
- ✅ `deploy/production-enablement-checklist.md` — 变量/迁移/验证/回滚齐备；
- ✅ 门禁：ruff F821 0、import OK、Alembic 单头、scan HARD 0、cconditions 0 硬错、
  vitest 352/352、pytest 1133 passed/3 skipped。

## 判决

**APPROVED**。合入前置：① 用户一次总确认；② 首轮审计；③ required checks 全绿后最终审计。

## 下一批次 Leader 条件

- **C106-1**: 生产切换人工步骤（用户确认窗口后）：备份 Supabase → Railway 新增
  REGISTRATION_ENABLED=true/INVITE_CODE_REQUIRED=true/配额变量 → `alembic upgrade head`
  → 按清单 §4 验证 → 回填清单 §6 并关闭 C104-2/C105-2。
- **C106-2**: 邀请链接灰度观察：一周内统计链接转化（注册→入项目）与滥用（无效 token 尝试），
  评估是否需要邮件通知与防刷（速率限制/验证码）。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 并行批次合入产生 Alembic merge 头，新迁移父节点写旧头导致多头 | 开工先 `alembic heads` 确认基线；本批修正 down_revision | 迁移文件 + QA B106-1 |
| 生产切换依赖外部凭据/窗口 | 登记人工步骤 C106-1，不阻塞代码合入 | C106-1 + checklist |
| C105-1/C104-4 完成 | 关闭并登记本批 PR 证据 | C-CONDITIONS Closed 表 |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 5–7h vs ≈6h | 0/1/0/2 | 2 | 外部批次合入 + 契约漂移 | 开工先查 Alembic 头；断言用 objectContaining |

## 技能使用

- `cameltv-agent-team`/`cameltv-bug-guard`/`cameltv-ui-conventions`/`test-case-design` → 见 QA；
- 知识审计：组织权限映射与邀请链接设计决策具备入库价值，随 C106 条件跟踪。
