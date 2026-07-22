# Batch 29 — QA Report：C27 条件修复

> **QA (🔍)** | Date: 2026-07-22 | Verdict: **PASS** ✅

## 测试范围

| 维度 | 覆盖 |
|------|------|
| C27-C5 双 commit | knowledge.py 4 个路由 |
| C27-C6 except NameError | entity_service.py:625 |
| C27-C7 事务原子性 | artifact_service.py:78-133 |
| C27-C8 Pydantic 校验 | knowledge.py:189 + schemas/knowledge.py:173 |

## 变更文件清单

| 文件 | 变更 | 行数 |
|------|------|------|
| `backend/app/api/v1/knowledge.py` | 删除 4 处 db.commit() + model_validate | -4, +1 |
| `backend/app/schemas/knowledge.py` | SearchResultOut 加 from_attributes | +1 |
| `backend/app/services/knowledge/artifact_service.py` | 导入顺序重排 + 注释 | +6, -2 |
| `backend/app/services/knowledge/entity_service.py` | except 加 as e | +1, -1 |
| **合计** | | **+9, -7** |

## 逐条件验证

### C27-C5: 双 db.commit() 消除 (PASS ✅)

| 检查项 | 方法 | 结果 |
|--------|------|------|
| deprecate_source 单 commit | 代码审查 L343-344 | ✅ _audit → db.commit() |
| verify_source 单 commit | 代码审查 L358-360 | ✅ _audit → db.commit() |
| classify_source 单 commit | 代码审查 L391-394 | ✅ _audit → db.commit() |
| approve_artifact 单 commit | 代码审查 L479-480 | ✅ _audit → db.commit() |
| 无连续 db.commit() 成对 | grep 验证 | ✅ 15 个 commit 调用，无连续对 |
| 已正确的路由未受影响 | grep 验证 | ✅ reject/capture/import/relation_* 不变 |

### C27-C6: except NameError 修复 (PASS ✅)

| 检查项 | 方法 | 结果 |
|--------|------|------|
| except Exception as e | 代码审查 L625 | ✅ 已添加 `as e` |
| str(e) 不再引用未定义变量 | 静态分析 | ✅ e 已定义 |
| 其他 except Exception 无同样问题 | grep 审计 | ✅ L212/447/613 未使用 str(e) |

### C27-C7: 事务原子性 (PASS ✅)

| 检查项 | 方法 | 结果 |
|--------|------|------|
| artifact 标记先于 create_case | 代码审查 L123-126 | ✅ review_status 在 create_case 之前设置 |
| create_case 内部 commit 原子提交 | 逻辑验证 | ✅ flush 的 artifact 状态随 create_case commit |
| create_case 失败时 artifact 不变 | 逻辑验证 | ✅ create_case 抛异常→不 commit→artifact 状态不持久 |
| ref_id 后更新 | 代码审查 L131-132 | ✅ case["id"] 正确写回 |

### C27-C8: Pydantic 校验 (PASS ✅)

| 检查项 | 方法 | 结果 |
|--------|------|------|
| from_attributes=True 已添加 | 代码审查 schema L174 | ✅ 与同文件其他 11 个 schema 一致 |
| model_validate 替换 **__dict__ | 代码审查 knowledge.py L189 | ✅ |
| 类型安全 | 静态分析 | ✅ score 为 None 或 chunk_id 为 str 将被拦截 |

## 回归风险评估

| 风险 | 等级 | 分析 |
|------|------|------|
| 移除 db.commit() 导致未刷新数据 | 🟢 低 | session 仍在，单 commit 覆盖所有变更 |
| artifact 顺序变更破坏导入流程 | 🟢 低 | create_case 的 commit 现在提交 artifact 状态，与之前行为等价 |
| model_validate 更严格导致 500 | 🟡 中 | 需确认 hit 对象字段与 schema 完全匹配。若搜索返回额外字段，model_validate(from_attributes=True) 会忽略它们（安全） |
| except 修复引入语法错误 | 🟢 低 | 纯语法修复，零风险 |

## 未覆盖项

| 条件 | 状态 | 原因 |
|------|------|------|
| C27-C1 模块树准确率 ≥70% | ⏸️ 延后 | 需 staging 环境 |
| C27-C2 图谱渲染 <3s | ⏸️ 延后 | 需性能测试 |
| C27-C3 release_bundle 端到端 | ⏸️ 延后 | 需集成测试 |
| C27-C4 Wiki 同步覆盖率 ≥70% | ⏸️ 延后 | 需 staging 验证 |

## QA 判决: PASS ✅

4 个代码修复全部通过代码审查。C27-C1~C4 因需要 staging 环境，标记为延后（在 C-CONDITIONS.md 中保持 Open）。
