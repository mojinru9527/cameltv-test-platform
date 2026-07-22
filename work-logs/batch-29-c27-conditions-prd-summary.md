# Batch 29 — PRD Summary：C27 Leader 条件修复

> **Product (🟦)** | Date: 2026-07-22 | Version: v1.0

## C-CONDITIONS.md 预检

根据 `C-CONDITIONS.md`，batch-27 Knowledge Sphere 合入后遗留 8 个 Open 条件：

| ID | 内容 | 优先级 | 类型 |
|----|------|--------|------|
| C27-C1 | 模块树自动提取准确率 ≥70% | P1 | 验证 |
| C27-C2 | 图谱层级视图在 200 节点下渲染时间 <3s | P1 | 验证 |
| C27-C3 | release_bundle 创建流程端到端可用 | P1 | 验证 |
| C27-C4 | Wiki 基线同步覆盖率 ≥70% | P1 | 验证 |
| C27-C5 | 修复 8 处双 db.commit() 为单 commit | P1 | 代码修复 |
| C27-C6 | 修复 entity_service.py:625 except NameError | P1 | 代码修复 |
| C27-C7 | 修复 import_to_test_case 事务原子性 | P1 | 代码修复 |
| C27-C8 | 修复 SearchResultOut 绕过 Pydantic 校验 | P1 | 代码修复 |

## 问题陈述

Batch 27 Knowledge Sphere 在 QA v2.0 实现审查中发现了 **4 个代码缺陷**（C27-C5~C8）和 **4 个验证缺口**（C27-C1~C4）。代码缺陷存在数据一致性风险，验证缺口需要 staging 环境支持。

**用户关心的原因**：
- 双 commit 导致业务操作和审计日志不在同一事务——操作成功但审计丢失时无法追溯
- except NameError 导致图谱演化异常时错误处理自身崩溃，掩盖真实故障
- 事务非原子性导致 AI 用例导入时可能"用例已创建但产物未标记"，产生孤儿数据
- Pydantic 校验绕过使搜索 API 返回的数据结构不可信，前端可能收到类型错误的数据

## 成功指标

| 指标 | 目标 | 验证方式 |
|------|------|---------|
| 双 commit 消除 | knowledge.py 中 0 个双 commit 模式 | 代码审查 + grep |
| except 修复 | entity_service.py:625 可正常捕获异常 | 代码审查 |
| 事务原子性 | import_to_test_case 全流程单事务 | 代码审查 |
| Pydantic 校验 | SearchResultOut 使用 model_validate | 代码审查 |
| 后端启动 | 零 ImportError/NameError | `uvicorn` 启动检查 |

## 非目标（明确排除）

- **C27-C1~C4**：需要 staging 环境或人工验证，**本批次不纳入**。在 C-CONDITIONS.md 中保持 Open，标注为"需 staging 环境"
- **性能优化**：不涉及图谱查询性能、搜索响应时间优化
- **新功能**：不新增任何功能，仅做缺陷修复

## 用户故事

### US-1: 修复双 db.commit() 事务一致性 (C27-C5)

**Given** 管理员通过知识中心 API 执行废弃/验证/分类/审批操作
**When** 审计日志写入失败（DB 连接中断、磁盘满等）
**Then** 业务操作也应回滚，保证操作和审计日志的原子性

**涉及路由**（4 个）：
1. `POST /sources/{id}/deprecate` — 废弃知识源
2. `POST /sources/{id}/verify` — 验证知识源保鲜度
3. `PATCH /sources/{id}/classify` — 更新知识源分类
4. `POST /ai-artifacts/{id}/approve` — 采纳 AI 产物

### US-2: 修复图谱演化异常处理 NameError (C27-C6)

**Given** 图谱自演化过程中发生异常（如 session 失效）
**When** except 块执行 `str(e)` 获取异常消息
**Then** 不应因 `except Exception:` 缺少 `as e` 而触发二次 NameError

### US-3: 修复 AI 产物导入事务原子性 (C27-C7)

**Given** 审核通过的 AI 用例产物等待导入正式用例库
**When** `import_to_test_case` 在 `create_case` 成功后、标记 `review_status='imported'` 前发生异常
**Then** 整个操作应回滚，不留孤儿用例（已创建但未关联产物的用例）

### US-4: 修复搜索 API Pydantic 校验绕过 (C27-C8)

**Given** 用户通过 `/knowledge/search` 执行混合检索
**When** `hit.__dict__` 包含 schema 未定义的字段或类型不匹配
**Then** Pydantic 应在构造 `SearchResultOut` 时捕获并报错，而非静默传递脏数据

## 风险评估

| 风险 | 等级 | 缓解 |
|------|------|------|
| 移除 db.commit() 导致行为变化 | 🟢 低 | 其余路由已是单 commit 模式，已验证正确 |
| except 修复引入新问题 | 🟢 低 | 仅添加 `as e`，零逻辑变更 |
| 事务原子性修复破坏导入流程 | 🟡 中 | 需确认 `create_case` 的内部 commit 行为 |
| Pydantic 校验更严格导致搜索报错 | 🟡 中 | 需验证 hit 对象实际字段与 schema 一致 |

## 术语

- **双 commit 模式**：业务操作后 commit → 写审计日志 → 再 commit，两次 commit 破坏原子性
- **事务原子性**：一组操作要么全部成功，要么全部回滚
- **model_validate**：Pydantic v2 的校验入口，会检查字段类型和约束；`**__dict__` 展开绕过此检查
