# Batch 105 — Leader Verdict（租户模式）

> **Leader (🎯)** | Date: 2026-08-06 | Decision: APPROVED（待用户一次总确认 + PR required checks 全绿后合入）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | 通过 | 组织模型/迁移回填/接口/访问控制闭环；19 新测试 + 全量 1116 通过 |
| 风险 | 低 | 个人组织不可停用、团队组织配额、组织成员访问收敛、超管全量不变 |
| 覆盖 | 通过 | US-01~05 全过；越权 403/配额 400/邀请失败 400/迁移幂等均有断言 |

## 关键决策（已批准）

1. **组织层采用「个人组织自动创建 + 团队组织自助创建」**：注册即有归属，项目默认挂个人组织，
   团队协作通过团队组织承载，无需人工开通。
2. **组织成员默认可见组织项目，业务权限仍走现有全局/项目角色**：避免引入组织级权限映射的
   复杂度；映射留作 C105-1 后续评估。
3. **邀请按用户名精确匹配，不暴露用户目录**：普通用户无法拉全量用户列表，防信息泄露。
4. **迁移防御式 + 幂等**：个人组织按 `personal-{user_id}` 编码唯一，重复执行不产生重复组织。

## 抽检通过

- ✅ `backend/app/services/organization_service.py` — 幂等个人组织 + 配额 + 角色常量；
- ✅ `backend/app/core/deps.py:require_project` — 项目成员/组织成员/超管三分支；
- ✅ `backend/app/alembic/.../20260806_batch105_organization.py` — 建表+回填+防御式；
- ✅ `backend/app/api/v1/organization.py` — 按用户名邀请、组织成员项目列表；
- ✅ `frontend/src/pages/organization/index.tsx` — 四态/中文角色/个人组织禁停用；
- ✅ 门禁：ruff F821 0、import OK、Alembic 单头、scan HARD 0、cconditions 0 硬错、
  vitest 350/350、pytest 1116 passed/3 skipped（退出码记录于 QA）。

## 判决

**APPROVED**。合入前置：① 用户一次总确认；② 首轮审计；③ required checks 全绿后最终审计。

## 下一批次 Leader 条件

- **C105-1**: 评估组织级角色→业务权限映射（如「组织管理员=组织内全部项目管理员」）与
  组织申请/审批流；不引入映射前保持现状（组织成员仅获得访问权）。
- **C105-2**: 生产启用租户层前执行：存量迁移演练（含 PostgreSQL）、确认
  `REGISTRATION_ENABLED`/配额监控（承接 C104-2）；结果登记交付清单。
- **C105-3**: `frontend/src/types/api.d.ts` 全量重生成（C104-3 持续跟踪，工具版本锁定）。
- **C105-4**: 「停用组织后组织成员入口提示」的 UI 走查与「组织项目联动」补浏览器截图证据
  （P3-04 落实确认）。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 服务函数返回类型变更破坏 ORM 消费者（dashboard） | 恢复 ORM 返回 + 接口层 enrich；经验入 QA/判决 | `project_service.py::projects_for_user` + 本判决 |
| 迁移对最小旧库脆弱（batch48 测试无 sys_project） | 防御式跳过回填 | 迁移文件 + QA B105-2 |
| TestClient cookie 串号再次出现 | 测试辅助函数统一登录后清 cookie（T3 已有先例） | 组织测试文件 |
| C104-1 完成 | 关闭并登记本批 PR 证据 | C-CONDITIONS Closed 表 |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 4–6h vs ≈5h | 0/1/1/2 | 2 | 契约变更 + 测试陈旧 | 改返回类型先查调用方；迁移兼容最小旧库 |

## 技能使用

- `cameltv-agent-team`/`cameltv-bug-guard`/`cameltv-ui-conventions`/`test-case-design` → 见 QA；
- 知识审计：组织层设计决策（个人组织自动创建、组织成员可见性、邀请不暴露目录）具备入库价值，
  随 C105 条件跟踪，运行中知识库可用后 ingest。
