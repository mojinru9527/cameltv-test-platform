# Batch 29 — PM Plan：C27 Leader 条件修复

> **PM (🟨)** | Date: 2026-07-22 | Version: v1.0

## 任务拆解

本批次为纯代码修复批次，无前端变更，无新增依赖。

### M1: 代码修复（4 任务，预估 120 分钟）

---

### T1: 修复 4 处双 db.commit() (C27-C5) ⏱ 40 min

**描述**：在 knowledge.py 的 4 个路由中移除第一个 `db.commit()`，使业务操作和审计日志在同一事务中提交。

**涉及文件**：`backend/app/api/v1/knowledge.py`

**变更点**（4 处）：
| 路由 | 行号 | 操作 |
|------|------|------|
| `deprecate_source` | L343 | 删除 `db.commit()` |
| `verify_source` | L360 | 删除 `db.commit()` |
| `classify_source` | L394 | 删除 `db.commit()` |
| `approve_artifact` | L482 | 删除 `db.commit()` |

**验收标准**：
- [ ] 4 处路由的函数体内只剩一个 `db.commit()`（在 `_audit()` 之后）
- [ ] 无功能逻辑变更
- [ ] `grep 'db.commit()' knowledge.py` 输出的连续双 commit 模式消失

**参考**：其余路由（reject_artifact, capture, import_artifact 等）已是单 commit 模式

---

### T2: 修复图谱演化 except NameError (C27-C6) ⏱ 15 min

**描述**：在 entity_service.py L625 的 `except Exception:` 后添加 `as e`。

**涉及文件**：`backend/app/services/knowledge/entity_service.py:625`

**变更**：
```python
# Before
except Exception:

# After
except Exception as e:
```

**验收标准**：
- [ ] `str(e)` 不再引用未定义变量
- [ ] 无其他逻辑变更

---

### T3: 修复 AI 产物导入事务原子性 (C27-C7) ⏱ 35 min

**描述**：`import_to_test_case` 在 `create_case` 成功后若后续步骤失败，已创建的用例不会回滚。需确保整体事务原子性。

**涉及文件**：`backend/app/services/knowledge/artifact_service.py:78-127`

**分析**：
- L121: `test_case_service.create_case(db, data)` — 注释说 "commits internally"
- L123-126: 更新 `row.review_status` + `db.flush()`
- 如果 `create_case` 内部 commit 了，那即使后面的 flush 失败，用例也已入库

**方案**：检查 `create_case` 是否真的内部 commit。若是，将 artifact 状态更新包装为：先 flush artifact 状态，再调用 create_case（或改造 create_case 为不自动 commit）。

**验收标准**：
- [ ] `create_case` 失败时 artifact 保持 `approved` 状态（可重试）
- [ ] artifact 状态更新失败时用例不创建（或用例创建失败时 artifact 不标记 imported）
- [ ] 不引入新的 Session 管理问题

---

### T4: 修复搜索 Pydantic 校验绕过 (C27-C8) ⏱ 15 min

**描述**：将 `SearchResultOut(**hit.__dict__)` 改为 `SearchResultOut.model_validate(hit)`。

**涉及文件**：`backend/app/api/v1/knowledge.py:189`

**变更**：
```python
# Before
return R.ok([SearchResultOut(**hit.__dict__) for hit in hits])

# After
return R.ok([SearchResultOut.model_validate(hit) for hit in hits])
```

**验收标准**：
- [ ] 搜索 API 返回结果结构不变
- [ ] 若 hit 缺少必填字段，Pydantic 抛出 ValidationError（而非静默传递）
- [ ] `hit` 对象需支持 `model_validate`（即 from_attributes 需启用或使用 `model_validate(hit.__dict__)` 回退）

---

### M2: 验证与收尾 ⏱ 30 min

- T5: 后端启动检查（`uvicorn` 无 ImportError/NameError）
- T6: 更新 C-CONDITIONS.md — C27-C5~C8 → Closed，C27-C1~C4 标注"需 staging 环境"

## 总预估

| 阶段 | 任务 | 耗时 |
|------|------|------|
| M1 | T1-T4 代码修复 | 105 min |
| M2 | T5-T6 收尾 | 30 min |
| **合计** | | **135 min** |
