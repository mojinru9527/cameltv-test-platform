# Batch 27 "Knowledge Sphere" — QA Report v2.0

> **审查日期**：2026-07-22
> **审查范围**：M1 数据模型 → M5 迁移+集成，全栈（后端 + 前端 + 数据库 + 脚本）
> **审查方法**：静态代码审查 + 架构分析 + 边界条件测试
> **总代码量**：~5,718 行新增（32 文件）+ 若干已有文件修改

---

## 判决：⚠️ CONDITIONAL PASS（附带 6 个阻塞项）

代码覆盖了 Batch 27 设计目标的核心功能（知识源管理、RAG 检索、知识图谱、Wiki 同步、Skills 模板、迭代管理），但发现了 **6 个 P0 阻塞项** 和 **7 个 P1 高危项**，必须修复后才能合并到 develop。

---

## P0 — 阻塞（修复前禁止合入）

### P0-1: `String` 类型未导入导致后端无法启动
- **文件**：[models/knowledge.py:44](test-platform-v2/backend/app/models/knowledge.py#L44)
- **证据**：第 11 行仅导入 `from sqlalchemy import LargeBinary, Text`，但第 44 行使用了 `mapped_column(String(200), default=None)`
- **影响**：导入 `models/knowledge` 模块时抛出 `NameError: name 'String' is not defined`，**整个后端无法启动**
- **修复**：在第 11 行添加 `String` 到导入列表：
  ```python
  from sqlalchemy import LargeBinary, String, Text
  ```

### P0-2: 3 个 Wiki 模型未注册到 `models/__init__.py`——表不会自动创建
- **文件**：[models/__init__.py](test-platform-v2/backend/app/models/__init__.py#L43-L50)
- **证据**：`ExternalWikiConnection`、`WikiLintReport`、`WikiLintIssue` 在 `models/wiki.py` 中定义但不在此文件的导入列表中
- **影响**：`Base.metadata.create_all()` 不会创建这 3 张表。Wiki API 路由中：
  - `wiki.py` 导入并使用 `ExternalWikiConnection`（line 19）
  - `wiki.py` 导入并使用 `WikiLintReport`、`WikiLintIssue`（line 20）
  - 首次访问这些表时 SQLAlchemy 会抛出 `OperationalError: no such table`
- **修复**：在 `models/__init__.py` 的 wiki 导入块（line 43-50）中添加这 3 个模型

### P0-3: `graph_view` 的 `knowledge_domain` LEFT JOIN 过滤器有 bug——静默丢弃无源实体
- **文件**：[api/v1/knowledge.py:608-612](test-platform-v2/backend/app/api/v1/knowledge.py#L608-L612)
- **证据**：
  ```python
  stmt = stmt.outerjoin(
      KnowledgeSource, KnowledgeEntity.source_id == KnowledgeSource.id
  ).where(KnowledgeSource.knowledge_domain == knowledge_domain)
  ```
  LEFT JOIN 的右表上的 `WHERE` 条件会将其转换为 INNER JOIN
- **影响**：过滤 `knowledge_domain` 时，所有 `source_id IS NULL` 的实体被静默丢弃。图谱视图不完整
- **修复**：将 WHERE 条件移到 JOIN ON 子句中：
  ```python
  stmt = stmt.outerjoin(
      KnowledgeSource,
      (KnowledgeEntity.source_id == KnowledgeSource.id)
      & (KnowledgeSource.knowledge_domain == knowledge_domain),
  )
  ```
  或重建为子查询过滤 source_id 所在的集合

### P0-4: `release-bundles` 前端页面引用了不存在的 API 文件——编译失败
- **文件**：[pages/release-bundles/index.tsx:5-8](test-platform-v2/frontend/src/pages/release-bundles/index.tsx#L5-L8)
- **证据**：该文件 `import { createReleaseBundle, deleteReleaseBundle, fetchReleaseBundles } from '@/api/releaseBundles'`，但：
  - `api/releaseBundles.ts` 文件不存在
  - 后端没有 `release_bundle` 相关的路由/模型/API
  - `/release-bundles` 路由未在 `router/index.tsx` 中注册
- **影响**：如果代码在任何地方引用了此页面（即使作为 lazy import），都会在 Vite 编译时抛错。即使未被引用，这也是一段死代码
- **修复**：删除 `pages/release-bundles/index.tsx` 和 `pages/release-bundles/` 目录，待后续批次重新实现

### P0-5: 缺少 Alembic 迁移—— `module_name` 列、Wiki Lint 表等没有迁移
- **背景**：当前使用 `AUTO_CREATE_TABLES=true` 自动建表（开发模式），但生产环境需要 Alembic 迁移
- **影响范围**：
  - `knowledge_source.module_name`（String 200）——无迁移
  - `knowledge_iteration`、`knowledge_snapshot`——无迁移
  - `wiki_raw_source`、`wiki_page`、`wiki_link`、`wiki_ingest_job`、`wiki_diff_task`、`wiki_diff_item`——已有迁移 `20260710_0017_wiki_tables.py`
  - `external_wiki_connection`、`wiki_lint_report`、`wiki_lint_issue`——无迁移（也与 P0-2 相关）

  需要补充的迁移（等 P0-2 修复后一起生成）：
    1. `knowledge_source.module_name` 列（Batch 27 期间新增）
    2. `knowledge_iteration` 表（M6）
    3. `knowledge_snapshot` 表（M6）
    4. `external_wiki_connection` 表
    5. `wiki_lint_report` 表
    6. `wiki_lint_issue` 表
- **修复**：运行 `alembic revision --autogenerate -m "batch27_complete_schema"` 生成完整迁移

### P0-6: Agent Team 工件全部缺失
- **证据**：`work-logs/` 目录下没有任何 `batch-27-*` 文件
- **缺失项**：
  - `batch-27-knowledge-sphere-prd-summary.md` ❌
  - `batch-27-knowledge-sphere-pm-plan.md` ❌
  - `batch-27-knowledge-sphere-design-spec.md` ❌
  - `batch-27-knowledge-sphere-qa-report.md` ❌（本报告即为补写）
  - `batch-27-knowledge-sphere-leader-verdict.md` ❌
  - `work-logs/kanbans/DEV-knowledge-sphere.md` ❌
- **影响**：违反 Agent Team 门禁（`[[agent-team-gate]]`），所有涉及 `test-platform-v2/` 的改动必须过六部门流水线
- **修复**：Product/PM/Design/Leader 部门逐个产出工件

---

## P1 — 高危（影响功能正确性或数据完整性）

### P1-1: 8 个路由函数中双 `db.commit()` 模式——审计日志写入失败时主变更无追踪
- **文件**：[api/v1/knowledge.py](test-platform-v2/backend/app/api/v1/knowledge.py)
- **具体位置**：
  - `deprecate_source`：line 343 → 345
  - `verify_source`：line 360 → 362
  - `classify_source`：line 394 → 397
  - `capture_insight`：line 430 → 431
  - `approve_artifact`：line 482 → 484
  - `reject_artifact`：line 500 → 502
  - `extract_graph`：line 542 → 543
  - `evolve_graph`：line 712 → 713
- **风险场景**：第一次 `db.commit()` 成功→`_audit()` 异常→第二次 `db.commit()` 未执行。结果：变更已持久化但无审计日志
- **修复**：合并为单次 commit：先 `_audit()`（flush），再 `db.commit()`

### P1-2: `import_to_test_case` 在路由事务中提交——破坏原子性
- **文件**：[services/knowledge/artifact_service.py:120](test-platform-v2/backend/app/services/knowledge/artifact_service.py#L120)
- **证据**：`case = test_case_service.create_case(db, data)  # commits internally`
- **风险**：路由函数 `import_artifact`（line 507-518）在同一个 `db` Session 中先提交了 `test_case`，然后又提交了 artifact 状态更新和审计。如果审计写入失败，用例已经插入库中但 artifact 状态未更新
- **修复**：让 `create_case` 仅 flush 不 commit，由路由统一 commit；或将该端点全程改用独立 Session

### P1-3: `SearchResultOut(**hit.__dict__)` 绕过 Pydantic 校验
- **文件**：[api/v1/knowledge.py:189](test-platform-v2/backend/app/api/v1/knowledge.py#L189)
- **证据**：`return R.ok([SearchResultOut(**hit.__dict__) for hit in hits])`
- **对比**：同一文件中其他模型均使用 `KnowledgeSourceBrief.model_validate(r)` 的规范方式
- **风险**：绕过 Pydantic 的类型强制转换和校验。如果 `SearchHit` 有类型错误的字段，响应会包含无效数据而非抛明确的 500 错误
- **修复**：改为 `SearchResultOut.model_validate(hit)`，并在 `SearchHit` dataclass 上添加 `model_config` 或改用 Pydantic BaseModel

### P1-4: `graph_view` 的 knowledge_domain 过滤性能差——每次 JOIN 整个 KnowledgeSource 表
- **文件**：[api/v1/knowledge.py:608-612](test-platform-v2/backend/app/api/v1/knowledge.py#L608-L612)
- **影响**：当 KnowledgeSource 有几百万行时，LEFT JOIN（修复后仍需 JOIN）会拖慢查询
- **修复**（与 P0-3 一并处理）：先查询符合条件的 `source_id` 集合，再用 `WHERE source_id IN (...)` 或 `WHERE source_id IS NULL` 的 OR 条件

### P1-5: `platform_doc` / `capture` / `agent_*` 类知识源未自动设 `knowledge_domain="platform"`
- **文件**：[services/knowledge/source_service.py:80-95](test-platform-v2/backend/app/services/knowledge/source_service.py#L80-L95)
- **证据**：`record_source()` 创建 KnowledgeSource 时不设置 `knowledge_domain`，依赖模型默认值 `"project"`。只有 `ingest_capture_in_new_session`（line 641）和 `ingest_platform_knowledge_in_new_session`（line 578）在 `record_source` 后显式设置了 `src.knowledge_domain`
- **风险**：`platform_doc`、`agent_*` 类知识源被错误分类为 `project`，除非后续手动分类
- **修复**：在 `record_source()` 中添加 `knowledge_domain` 参数，默认为 `None`（不覆盖），调用方按需传入。或者在迁移脚本中补充分类逻辑

### P1-6: 审计详情 `classify_source` 的 detail 信息未经脱敏
- **文件**：[api/v1/knowledge.py:396](test-platform-v2/backend/app/api/v1/knowledge.py#L396)
- **证据**：`detail=f"para={body.para_category} domain={body.knowledge_domain}"`
- **风险**：PARA category 和 domain 值是用户输入，虽已经过白名单校验（line 381-386），但 detail 格式未统一，审计日志可读性差异大
- **修复**：影响较小，改进为统一格式。非阻塞

### P1-7: 迁移脚本中 `metadata_json` 的 `knowledge_domain` 解析有 bug
- **文件**：[scripts/migrate_knowledge_domain.py:91-98](test-platform-v2/backend/scripts/migrate_knowledge_domain.py#L91-L98)
- **证据**：
  ```python
  if metadata_json and '"knowledge_domain"' in metadata_json:
      md = json.loads(metadata_json)
      if isinstance(md, dict) and md.get("knowledge_domain") == "platform":
          return "platform"
  ```
- **问题**：这个检查只能返回 `"platform"`——即使用户手动把 metadata 中的 domain 设成了 `"project"`，这里也无法纠正过来。不过这是迁移脚本的防御性代码，实际分类走前几条规则。低实际影响

---

## P2 — 中等（代码质量 / 边界条件 / 可维护性）

### P2-1: `import` 在函数底部而非顶部——违反代码风格
- **文件**：[api/v1/knowledge.py:771](test-platform-v2/backend/app/api/v1/knowledge.py#L771)
- **证据**：`from app.services.knowledge import snapshot_service` 在 /iterations 代码块之前
- **影响**：降低代码可读性。此导入用于 `compare_iterations` 和 `get_snapshots`，应与文件顶部的其他 import 放在一起
- **修复**：移到文件顶部（line 55 附近）

### P2-2: `_build_relations` 关系发现复杂度高——大规模实体集可能超时
- **文件**：[services/knowledge/entity_service.py:231-356](test-platform-v2/backend/app/services/knowledge/entity_service.py#L231-L356)
- **分析**：`entity_source_map` 对每个 source 做 O(n²) 配对扫描。500+ 实体时可感知延迟
- **修复**：可延后到需要时优化。当前 `max_chunks=100` 限制可防止过度增长

### P2-3: `json.loads` 调用缺少 try/except 保护——数据库脏数据可导致 API 500
- **文件**：[api/v1/knowledge.py:666](test-platform-v2/backend/app/api/v1/knowledge.py#L666) / line 634（`reject_relation` 中相同）
- **证据**：`rel.metadata_json = json.dumps({**json.loads(rel.metadata_json or "{}"), "comment": body.comment})`
- **风险**：如果数据库中某条 `knowledge_relation.metadata_json` 已被手改为非法 JSON（极端情况），approve/reject API 会抛 500
- **修复**：用 try/except 包裹 `json.loads`；失败时使用 `{"comment": body.comment}` 作为 metadata_json

### P2-4: `ingest_lanhu_version_diff` 中包含硬编码 emoji——Windows GBK 兼容性
- **文件**：[services/knowledge/ingest_service.py:460](test-platform-v2/backend/app/services/knowledge/ingest_service.py#L460)
- **证据**：`emoji = {"new": "🆕", "modified": "✏️"}.get(p["change_type"], "")`
- **影响**：低。仅影响存储的 content 字段（UTF-8 编码的 SQLite），不影响终端输出

### P2-5: 前端 `SourceListTab.tsx` 有未提交修改
- **证据**：git status 显示 `M test-platform-v2/frontend/src/pages/knowledge/components/SourceListTab.tsx`
- **影响**：待确认改动内容。需审查并决定是提交还是丢弃

---

## P3 — 低（改进建议 / 防御性编码）

### P3-1: `/knowledge/search` 和 `/knowledge/graph/extract` 无速率限制
- 这些是昂贵操作（向量搜索 / LLM 调用），建议添加速率限制装饰器

### P3-2: `evolve_graph` 中的 `except` 子句使用了原始异常
- **文件**：[services/knowledge/entity_service.py:627](test-platform-v2/backend/app/services/knowledge/entity_service.py#L627)
- 第 625 行的 `except Exception:` 中没有捕获异常对象，但第 628 行用了 `str(e)`——这会引用上层作用域中的变量（如果存在的话）。实际上这里 `e` 在 `except Exception as e:` 未绑定，会导致 `NameError`
- 修复：`except Exception as e:`

### P3-3: M5.2 POC 脚本的 DeepSeek API key 无效
- **状态**：已知问题，API key 返回 401
- **建议**：更新 key 后重新运行 POC 以获得真实准确率数据

### P3-4: `AgentRun` 和 `AgentQueueItem` 缺少 `TimestampMixin`
- **文件**：[models/knowledge.py:141](test-platform-v2/backend/app/models/knowledge.py#L141) / line 163
- `AgentRun` 有手写的 `created_at` / `finished_at`，`AgentQueueItem` 也有手写的时间戳
- 其他模型如 `KnowledgeSource` 使用 `TimestampMixin`（提供 `created_at` + `updated_at`）
- 不一致但非 bug；Agent 模型无 `updated_at` 的概念

---

## 架构健康评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 数据模型一致性 | 🟡 70% | 2 个模型导入遗漏（P0-2）、1 个类型导入遗漏（P0-1） |
| 事务安全性 | 🟡 65% | 8 个双 commit（P1-1）、1 个中途提交（P1-2） |
| 前端-后端契约 | 🟡 75% | 1 个死代码页面（P0-4）、1 个绕过 Pydantic（P1-3） |
| 数据库迁移完整性 | 🔴 50% | 6 张表/列缺少 Alembic 迁移（P0-5） |
| 流程合规性 | 🔴 40% | 6 个 Agent Team 工件缺失（P0-6） |
| 代码规范 | 🟢 85% | 少量风格问题（P2-1、P3-2） |
| 测试覆盖 | 🔴 30% | 仅 2 个前端组件测试，无后端 API 测试，无集成测试 |
| **综合** | **🟡 59%** | 6 个 P0 阻塞项需立即修复 |

---

## 修复优先级排序（建议修复顺序）

```
第 1 轮（5 分钟，修复即可启动后端）：
  1. P0-1: 添加 `String` 导入 → models/knowledge.py:11
  2. P0-2: 注册 3 个 wiki 模型 → models/__init__.py

第 2 轮（30 分钟，修复核心逻辑 bug）：
  3. P0-3: 修复 LEFT JOIN bug → api/v1/knowledge.py:608-612
  4. P1-1: 合并双 commit 模式 → api/v1/knowledge.py（8 处）
  5. P3-2: 修复 `except` 子句 → entity_service.py:625

第 3 轮（1 小时，数据完整性和合规）：
  6. P0-5: 生成 Alembic 迁移
  7. P1-2: 修复 import_to_test_case 事务
  8. P1-3: 改为 model_validate 模式

第 4 轮（清理和文档）：
  9. P0-4: 删除 release-bundles 死代码
  10. P0-6: 补写 Product/PM/Design/Leader 工件
```

---

## 测试建议

### 冒烟测试（修复 P0 必须通过）
1. **后端启动**：`uvicorn app.main:app` 不报错
2. **知识中心概览 API**：`GET /api/v1/knowledge/overview` 返回 200
3. **知识源列表 API**：`GET /api/v1/knowledge/sources?knowledge_domain=platform` 返回筛选结果
4. **图谱视图 API**：`GET /api/v1/knowledge/graph/view` 返回节点+边
5. **SQLite 表完整性**：所有 23 个知识/wiki 表可通过 `sqlite3 .tables` 列出

### 回归测试（修复后）
6. **Wiki 外部连接 CRUD**：`POST/GET/PUT/DELETE /api/v1/wiki/external-connections`
7. **Wiki Lint**：`POST /api/v1/wiki/lint` 返回报告
8. **前端页面**：`npm run build` 无编译错误
9. **域名迁移脚本**：`python scripts/migrate_knowledge_domain.py --dry-run` 显示 0 变更（已执行过）

---

## 正面发现

虽然以上列出了很多问题，但以下方面做得不错：

1. **全面的功能覆盖**：3 个路由模块 ~85 个端点，完整覆盖知识源 CRUD → RAG 检索 → 图谱 → Wiki → Skills → 迭代管理全链路
2. **架构分层清晰**：Router → Service → Model 分层严格，知识库服务使用独立 Session 防御性编程
3. **安全考虑周全**：`sanitize.py` 脱敏、CSV 密钥加密、治理守卫（`import_to_test_case` 必须审批通过）
4. **开关系统完善**：所有功能都有配置开关（`rag_enabled` / `knowledge_graph_enabled` / `wiki_enabled` 等），可渐进式上线
5. **M5 迁移脚本健壮**：CSV 快照 + spot-check + dry-run 三保险，Windows GBK 编码处理
6. **前端 12 Tab 设计**：从 PARA 项目/平台视角 + RAG 技术视角全面覆盖知识管理用例

---

## Leader 条件（供 Leader 裁决参考）

- **C1**：P0-1~P0-5 修复完毕后触发 CI 冒烟测试
- **C2**：Alembic 迁移在 staging 环境验证通过（`alembic upgrade head` 无报错）
- **C3**：补写至少 Product PRD + PM Plan 两个工件
- **C4**：下一批次（Batch 28）应包含后端 API 集成测试（至少覆盖 `/knowledge/overview`、`/knowledge/search`、`/knowledge/sources`）

---

*QA 部门 | 2026-07-22 | v2.0*
