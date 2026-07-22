# Batch 27 — QA 报告
> **QA (🔍)** | Date: 2026-07-22 | Verdict: NEEDS WORK (设计审查)

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 12 | 9 | 2 | 1 |

## 逐条件验证

### C1: 数据模型兼容性
**变更文件**: `requirement.py:34-35` (新增2字段), `knowledge.py:29` (新增1字段)
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 新增字段有默认值 | ✅ PASS | platform="", doc_type="rp", module_id=None |
| 不破坏现有查询 | ✅ PASS | 可选字段，ORM 自动处理 |
| Alembic 迁移可回滚 | ✅ PASS | 有 downgrade 脚本 |
| 索引设计合理 | ✅ PASS | module_id 索引，release_bundle 版本号索引 |

### C2: 知识图谱实体扩展
**变更文件**: 无 DDL 变更（entity_type/relation_type 是字符串字段）
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 新增实体类型与现有不冲突 | ✅ PASS | 7 种新类型使用独立前缀命名 |
| entity_key 格式规范唯一 | ⚠️ WARN | 见 D1 |
| 关系类型语义清晰 | ✅ PASS | 7 种新关系类型命名规范 |

### C3: API 设计完整性
**变更文件**: 新增 `release_bundle.py`, `requirement_module.py` 路由
| 检查项 | 结果 | 说明 |
|--------|------|------|
| CRUD 完整 | ✅ PASS | 发布包有完整 CRUD |
| 权限控制 | ⚠️ WARN | 见 D2 |
| Response Schema 设计 | ✅ PASS | 区分 ReleaseBundleOut / ReleaseBundleDetail |
| 分页支持 | ✅ PASS | 列表接口有 page/page_size |

### C4: 图谱性能
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 懒加载策略 | ✅ PASS | 按需展开子节点 |
| 初始加载量可控 | ✅ PASS | 仅加载 Project + 最新3个版本 |
| layout 选型合理 | ✅ PASS | hierarchical + physics:false |
| 极端情况 (200+ 节点) | ⚠️ WARN | vis-network 在 200+ 节点时可能卡顿，但 hierarchical 无物理模拟，风险可控 |

### C5: Wiki 基线同步
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 同步触发机制明确 | ✅ PASS | 导入时自动 + 手动触发 |
| 目录映射规则清晰 | ✅ PASS | 蓝湖→Wiki 路径映射表明确 |
| 差异对比粒度 | ✅ PASS | 按页面粒度（而非整文档） |

### C6: 前后端契约一致性
| 检查项 | 结果 | 说明 |
|--------|------|------|
| API Schema 与前端类型对齐 | ⚠️ WARN | 设计中未定义前端 TypeScript 类型 |
| 三态设计 (Loading/Empty/Error) | ✅ PASS | 设计规范中覆盖 |

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 建议 |
|---|--------|------|------|------|
| D1 | P2 | entity_key 格式中的 `module_name` 在跨版本时可能冲突——同一个模块名在 v1.0 和 v3.0 中含义不同 | entity_key 设计 `client_module:{project_name}:{module_name}` 缺少版本号 | 改为 `client_module:{project_name}:{version}:{module_name}`，或使用 `ReleaseBundle.client_version` 作为上下文隔离 |
| D2 | P2 | 新增 API 路由的权限标记使用了未定义的权限码 (`release_bundle:create` 等) | `POST /api/v1/release-bundles` 等接口缺少权限定义 | 复用现有权限体系（如 `requirement:upload`/`knowledge:manage`）或新增权限码并在 seed 脚本中注册 |
| D3 | P3 | `ModuleExtractor` 的启发式规则依赖蓝湖 URL 中的 parentId 关系——但 lanhu-mcp 并不总是能提取到完整的文件夹层级 | 实际蓝湖抓取中，文件夹层级信息可能不完整 | 增加 AI 辅助兜底：当 URL 层级缺失时，由 DeepSeek 分析页面名称和内容的相似度来推断模块归属 |

### 阻塞项

| # | 严重级 | 描述 |
|---|--------|------|
| B1 | P1 | **模块树自动提取的可行性未验证**。当前设计假设蓝湖证据包能提供足够的层级信息（parentId/文件夹归属），但实际的 `lanhu_evidence_page` 表是否包含这些字段？需要验证 `lanhu_evidence_page` 的实际数据结构。如果缺少层级信息，整个自动化流程需要大幅调整。 |

## 设计质量评估

| 维度 | 评分 | 备注 |
|------|------|------|
| 数据模型设计 | 8/10 | 层级模型完整，但 entity_key 需修正 |
| API 设计 | 7/10 | 功能完整，权限和错误处理待细化 |
| 兼容性 | 9/10 | 新增表+可选字段，对存量零影响 |
| 可扩展性 | 8/10 | 字符串类型字段，天然支持扩展 |
| 性能考量 | 8/10 | 懒加载+层级布局，性能可控 |
| 可实现性 | 6/10 | B1 阻塞——模块树自动提取依赖未验证 |

## 发布建议

**状态: NEEDS WORK**

**必修复 (阻塞)**:
- B1: 验证 `lanhu_evidence_page` 表是否包含层级信息（parentId/文件夹路径），否则需调整自动提取方案

**建议修复 (P2)**:
- D1: entity_key 含版本号
- D2: 权限码定义

**可延后 (P3)**:
- D3: AI 兜底提取逻辑
