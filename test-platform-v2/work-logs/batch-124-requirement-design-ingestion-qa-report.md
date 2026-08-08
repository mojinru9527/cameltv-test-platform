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
