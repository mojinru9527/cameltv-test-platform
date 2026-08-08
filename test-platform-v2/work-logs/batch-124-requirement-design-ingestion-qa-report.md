# Batch 124 — QA 报告（需求/设计稿入库 + 图谱 P0 崩溃修复）

> **QA (🔍)** | Date: 2026-08-08 | Verdict: 有条件通过（C124-1 生产导入验证、C124-2 图谱复测待部署）

## 1. 交付与证据

| # | 交付 | 证据 |
|---|------|------|
| 1 | 图谱 P0 崩溃修复：`graph_view` 节点/边去重（重复 entity_key 不再导致 vis-network add 抛错） | `api/v1/knowledge.py`；测试 1/1（重复实体→图谱不崩溃且节点唯一） |
| 2 | 需求/设计稿入库端点：`POST /knowledge/design-assets/import`（文本+图片 base64，按 content_hash 幂等）+ `GET /knowledge/design-assets/{id}/{file}`（路径逃逸防护） | `api/v1/knowledge.py`；测试 1/1（幂等+图片服务+逃逸防护） |
| 3 | 入库脚本：`scripts/knowledge/import-requirement-design.py`（读 HTML 功能点文本 + images/ 设计稿） | dry-run：147 页 / 116.5 万字符 / **3526 张设计稿图片**（平均 24 张/页） |
| 4 | 前端设计稿图片画廊：知识源详情 Sheet 展示设计稿截图（metadata.images） | `SourceListTab.tsx` |

## 2. 可执行门禁

| 门禁 | 结果 |
|------|------|
| 前端 `npm ci` / `typecheck` / `build` | ✅ / ✅ / ✅（8.58s） |
| 后端 ruff F821（changed 文件） | ✅ All checks passed |
| 后端 pytest（knowledge 相关 4 文件） | ✅ **79/79 passed** |
| app 导入 | ✅ knowledge router OK |

## 3. 缺陷/障碍

| # | 级别 | 问题 | 处理 |
|---|:----:|------|------|
| B124-1 | P2 | 需求/设计稿生产导入需部署后执行（147 页/3526 图片，API 上传量大） | 登记 C124-1 |
| B124-2 | P2 | 图谱 P0 修复需生产部署后复测（截图） | 登记 C124-2 |
| B124-3 | P3 | 全量 3526 张图片经 base64 API 导入耗时，建议分批/断点续传 | 登记建议（脚本已分批 5 页/批） |

## 4. 发布建议

状态: **有条件通过** ｜ 必修复: 0 ｜ 条件: C124-1/2（部署后生产导入+图谱复测）

## 5. 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1d / 实际 0.5d | 0/0/2/1 | 1 | 模块级导入遗漏（Path） | 新端点用到的模块级依赖先核对顶部导入；测试覆盖图片服务与逃逸防护 |

**技能使用**: `cameltv-bug-guard`（后端/脚本避坑）、`playwright-cli`/`vision`（生产走查复用）。

---

## 6. 补充 QA（2026-08-08 v2：用例基座接入 + 模块树全量修复）

### 交付与证据

| # | 交付 | 证据 |
|---|------|------|
| 5 | **功能用例 skill 接入 7 份功能用例文档**：新增权威输出要求 `tests/test-case-standards/功能测试输出用例要求.md`（设计前置/输出结构/覆盖维度/深度用例补充层）；`functional-checklist.md` v2 以它为主结构 | `功能测试输出用例要求.md` + `functional-checklist.md` |
| 6 | **两 skill 深度用例补充层**：SKILL.md 第 6 步强制 + functional-checklist 第四章 + api-checklist 末章 + case-template 深度用例模板（`闭环`/`状态机`/`关联` 标签） | `SKILL.md` / `api-checklist.md` / `case-template.md` |
| 7 | **后端加载权威输出要求**：`ai_service._load_skill_context_for` functional 加载 `功能测试输出用例要求.md`，api 加载 `接口测试输出用例要求.md`（skill 目录优先、规范中心兜底） | `ai_service.py` + 新测试 `test_ai_skill_context.py` **3/3** |
| 8 | **模块树全量修复**：`build_lanhu_hierarchy.py`（sitemap 全量解析 + enrich 回填截图）；运营后台 hierarchy **65→88 节点**（补齐 23 个「新增/编辑」等子页），用户端 **130 节点**（恢复 意见反馈/主播菜单/更新日志 3 页）；`requirement-module-tree.json` **192→218 节点**（35 模块/183 页/4781 设计稿） | `build_lanhu_hierarchy.py` + `requirement-module-tree.json`；校验：无重复 path、183 页 lanhu_page_id 全部可解析、depth≥3 父节点 0 缺失 |

### 可执行门禁（补充）

| 门禁 | 结果 |
|------|------|
| 后端 ruff F821（ai_service.py / build_lanhu_hierarchy.py） | ✅ All checks passed |
| 后端 pytest（test_ai_skill_context.py 3/3 + test_requirement_module_tree_import.py 1/1 + test_ai_extraction_fallback/test_ai_generate_chunked 7/7） | ✅ 11/11 |

### 说明

- 5 个用户端页面（启动页/开屏广告/权限获取/关于我们/通用组件）无设计稿截图目录，为真实页面但无截图，属正常空态。
- 用户端导出 `data/document.js` 为运营后台 sitemap 快照（不可用于用户端归级），故用户端走 enrich 模式保留既有功能地图归级。
- **补充说明**：`import-requirement-design.py`（QA 报告第 3 项引用的入库脚本）本轮补提交（此前仅 QA 记录、未入库）；dry-run 验证 运营后台 74 页/2776 图 + 用户端 109 页/2005 图，证据 `evidence/batch-124/design-assets-import-summary.json`。
- **基线失败说明**：`test_lanhu_provider.py` 2 项失败为 worktree 未初始化 `lanhu-mcp` 子模块所致（lanhu-mcp/requirements.txt 缺失 + lanhu_mcp_server 不可导入），与本次变更无关，属既有基线。
