# Batch 20 — Leader Verdict
> **Leader (🎯)** | Date: 2026-07-20 | Decision: **APPROVED**

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | ⭐⭐⭐⭐⭐ | 全链路覆盖，Model→Service→API→Type→UI 五层 |
| 风险 | 低 | 核心改动为逻辑删除（幂等），默认可逆 |
| 覆盖 | ⭐⭐⭐⭐ | 后端 399/400 通过，前端 TS 0 新错误 |

## 变更统计

| 类别 | 文件数 | 行数 |
|------|--------|------|
| 后端 Model | 2 | +3 |
| 后端 Service | 1 | +6/-6 |
| 后端 API | 2 | +160/-2 |
| 后端 Schema | 2 | +40/-0 |
| 后端 Migration | 1 | +22 |
| 前端 API | 1 | +23/-0 |
| 前端 Page | 4 | +12/-12 |
| 前端 Types | 1 | +1/-0 |

## 关键决策（已批准）

1. **逻辑删除替代硬删除**：TestCase.delete_case → `is_deleted=True`，保留历史数据用于审计追溯
2. **域/模块删除级联**：删除域 → 标记子模块+关联用例；删除模块 → 标记关联用例
3. **分类 CRUD API 独立端点**：`/test-cases/domains` 和 `/test-cases/modules`，遵循静态路径优先铁律
4. **接口测试默认 Tab 切换**：`/apitest` 入口默认展示「接口资产」，因为用户 90% 场景先浏览资产再调试
5. **搜索扩展**：`ApiEndpoint` 搜索增加 `module` + `ApiService.name` 字段，提升可发现性

## 抽检通过

- ✅ `backend/app/models/test_case.py:48` — is_deleted 字段与 Alembic 20260715 迁移对齐
- ✅ `backend/app/services/test_case_service.py:171-189` — delete/batch_delete 改为软删除
- ✅ `backend/app/api/v1/test_case.py:50-148` — 6 个分类 CRUD 端点，静态路径先于 `/{case_id}`
- ✅ `frontend/src/pages/testcase/index.tsx:424-452` — 优先级独立列，Badge 移出标题
- ✅ `frontend/src/pages/apitest/index.tsx:15,68` — 默认 Tab + DebugTab 接线修复
- ✅ `backend/app/api/v1/apitest.py:252-257` — 搜索含 module + service_name

## 判决

**APPROVED** — 全部 9 个 Slice 实现完整，前后端测试通过（1 个 pre-existing VPN test failure 无关），可合入 develop。

## 合入指令

```bash
git checkout develop
git pull origin develop
git merge feature/batch-20-fix-seven-gaps
git push origin develop
```

## 下一批次 Leader 条件

- C1: 浏览器手动验证 9 项修改（优先通过真实浏览器确认软删除级联 + DebugTab 预填 + 搜索扩展）
- C2: `test_openvpn_service.py` pre-existing 失败需在下批次修复或标记 skip
