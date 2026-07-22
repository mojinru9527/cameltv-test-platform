# Batch 29 — Design Spec：C27 代码修复

> **Design (🎨)** | Date: 2026-07-22 | Version: v1.0

## 概述

本批次为纯后端代码修复，无前端变更，无 API 接口变更，无新增依赖。

## 修复规格

### FIX-1: 消除双 db.commit() 模式 (C27-C5)

**文件**: `backend/app/api/v1/knowledge.py`

**模式识别**:

以下 4 个路由存在「先 commit 业务操作、后 commit 审计日志」的双 commit 模式：

```
路由                          | L1 (commit) | L2 (commit) | 正确模式
POST /sources/{id}/deprecate  | 343         | 345         | _audit → commit
POST /sources/{id}/verify     | 360         | 362         | _audit → commit
PATCH /sources/{id}/classify  | 394         | 397         | _audit → commit
POST /ai-artifacts/{id}/approve | 482       | 484         | _audit → commit
```

**对比 — 已正确的路由**（单 commit）:
- `reject_artifact` (L501): `_audit()` → `db.commit()` ✅
- `capture` (L431): `_audit()` → `db.commit()` ✅
- `import_artifact` (L517): `_audit()` → `db.commit()` ✅
- `relation_approve` (L668): `_audit()` → `db.commit()` ✅

**修复方案**:

删除第一个 `db.commit()`（审计日志之前的那个），保留审计之后的 `db.commit()`。

```python
# Before (deprecate_source 示例)
row = source_service.deprecate_source(db, source_id, ...)
if not row:
    return R(code=404, msg="知识源不存在")
db.commit()              # ← 删除此行
_audit(req, current, db, "knowledge:deprecate", f"source#{source_id}")
db.commit()              # ← 保留此行
db.refresh(row)

# After
row = source_service.deprecate_source(db, source_id, ...)
if not row:
    return R(code=404, msg="知识源不存在")
_audit(req, current, db, "knowledge:deprecate", f"source#{source_id}")
db.commit()
db.refresh(row)
```

**原理**: `_audit()` 调用 `audit_service.write_audit(db, ...)` 将审计记录 `db.add()` 到当前 Session。单次 `db.commit()` 同时提交业务变更和审计记录，保证原子性。

---

### FIX-2: 修复 except 缺少 as e (C27-C6)

**文件**: `backend/app/services/knowledge/entity_service.py:625`

```python
# Before — 异常对象未捕获，str(e) 引用未定义变量
except Exception:
    logger.exception("Graph evolution failed for project %s", project_id)
    db.rollback()
    return {"merged": 0, "confidence_updates": 0, "new_relations": 0, "error": str(e)}

# After — 正确捕获异常对象
except Exception as e:
    logger.exception("Graph evolution failed for project %s", project_id)
    db.rollback()
    return {"merged": 0, "confidence_updates": 0, "new_relations": 0, "error": str(e)}
```

**影响分析**:
- 当前：图谱演化异常 → except 块执行 → `str(e)` 抛出 NameError → 掩盖原始异常 → 调用方收到未捕获异常而非降级返回值
- 修复后：正确捕获异常 → 返回降级字典 → 调用方正常处理

---

### FIX-3: 修复事务原子性 (C27-C7)

**文件**: `backend/app/services/knowledge/artifact_service.py:78-127`

**现状问题**:

```python
# 当前顺序（有问题）
case = test_case_service.create_case(db, data)  # L121: 内部 db.commit() → 用例已入库
row.review_status = "imported"                  # L123: 仅修改属性
row.imported_ref_type = "test_case"             # L124
row.imported_ref_id = case["id"]                # L125
db.flush()                                      # L126: 刷入 session

# 如果 L123-126 中任一步失败 → 用例已存在但 artifact 仍为 'approved'
# → 重试会因 L92-93 被拒绝（"已导入"）
```

**修复方案**: 先更新 artifact 状态并 flush，再创建用例。`create_case` 内部 `db.commit()` 时会同时提交 artifact 状态变更。

```python
# After — 先标记 artifact，再创建用例
row.review_status = "imported"
row.imported_ref_type = "test_case"
row.imported_ref_id = 0  # 占位，create_case 成功后更新
db.flush()

case = test_case_service.create_case(db, data)  # 内部 commit 会提交 artifact 状态

# 更新 ref_id（create_case 的 commit 已提交了上面的 imported 标记）
row.imported_ref_id = case["id"]
db.flush()
# 调用方（knowledge.py 路由）随后 db.commit() 提交 ref_id 更新

return {"artifact_id": row.id, "case_id": case["id"]}
```

**关键决策**: 分两步 flush：
1. 第一次 flush + create_case 内部 commit → artifact 标记为 imported, 用例已创建
2. 第二次 flush ref_id + 调用方 commit → ref_id 写入

如果 create_case 失败 → artifact 状态变更和用例创建一起回滚（create_case 不 commit）。
如果第二次 flush 失败 → artifact 是 imported 但 ref_id=0（降级安全，可人工关联）。

---

### FIX-4: 修复 Pydantic 校验绕过 (C27-C8)

**文件**: `backend/app/api/v1/knowledge.py:189`

**SearchResultOut Schema** (`schemas/knowledge.py:173`):
```python
class SearchResultOut(BaseModel):
    chunk_id: int
    chunk_type: str
    title: str
    snippet: str
    score: float
    source_id: int
    source_name: str
```

**修复**:

```python
# Before — 绕过 Pydantic 校验
return R.ok([SearchResultOut(**hit.__dict__) for hit in hits])

# After — 通过 Pydantic 校验
return R.ok([SearchResultOut.model_validate(hit) for hit in hits])
```

**注意**: `model_validate` 在 `from_attributes=True` 配置下可直接接受 ORM 对象。需确认 `SearchResultOut` 的 `model_config`。若未启用 `from_attributes`，回退为：

```python
return R.ok([SearchResultOut.model_validate(hit.__dict__) for hit in hits])
```

**验收**: 搜索 API 返回数据格式不变，但类型错误（如 score 为 None、chunk_id 为 str）会被 Pydantic 拦截。

---

## 影响范围

| 维度 | 说明 |
|------|------|
| API 接口 | 无变更 — 所有端点路径/参数/响应格式不变 |
| 数据库 schema | 无变更 — 不新增/修改表或字段 |
| 前端 | 无变更 |
| 依赖 | 无新增 |
| 迁移 | 不需要 |
