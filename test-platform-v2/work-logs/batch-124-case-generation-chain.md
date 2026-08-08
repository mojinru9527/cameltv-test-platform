# Batch 124 — 用例生成链路补充（基座先行）

> **PM (🟨) 补充** | 2026-08-08

## 1. 用户确认的用例生成基座（强制）

所有用例生成必须走以下两个**经调整的基座 skill**，禁止脱离基座手写：

| 基座 | 位置 | 内容 |
|------|------|------|
| 功能用例规范 skill | `.agents/skills/test-case-design/SKILL.md` + `functional-checklist.md` + `case-template.md`；源规范 `tests/test-case-standards/功能测试用例规范.md` | 功能点分析 → 检查点 → 模板 → 覆盖率（每功能点 ≥1 正 +1 负） |
| 接口用例 skill | `.agents/skills/test-case-design/api-checklist.md`；源规范 `tests/test-case-standards/接口测试规范.md`、`API接口测试方案.md`、`接口测试考虑点【辅助作用】.md` | 入参/业务逻辑/返回值三类校验齐全 |

平台 `ai_service._build_system_prompt` 已加载 `test-case-design` skill（SKILL.md/case-template.md/functional-checklist.md）——即基座已在生成链路内。

## 2. 正确生成链路（全部体育模块）

```
蓝湖需求导出（用户端/运营后台 两目录，含层级+截图）
  → 需求文本+设计稿入库（knowledge design-assets）
  → 基座生成基础用例（功能用例规范 skill + 接口用例 skill，每功能点正/负用例）
  → 叠加深度用例（状态机/异常/闭环/关联/权限，Batch 122 模式）
  → 全部体育模块（用户端全模块 + 运营后台 14 模块 + konfi + 接口）
```

## 3. Batch A 差距说明（诚实）

Batch 122 深度用例是**手工编写**（依据原型功能点表），**未先经基座生成基础用例**。按用户要求，后续需：对全部体育模块先跑基座生成基础用例，再叠加深度用例；Batch 122 深度用例保留作为「深度层」。

## 4. 执行依赖

- 基座生成需 LLM（DeepSeek API Key，生产已配置；本地无 key）。
- 两个蓝湖导出目录已就绪：`backend/data/lanhu-exports/运营后台原型/`（74 页/2776 图）、`用户端原型/`（109 页/2005 图）。
- 基座生成的输入 = 需求文档（上传导出目录 → requirement doc → ai_service generate）。

## 5. 验收

- 每个体育模块：基础用例（基座生成，正/负/边界）+ 深度用例（叠加）双覆盖
- 用例可溯源到需求页（source_doc=lanhu_page_id）
- 功能用例走功能用例规范，接口用例走接口用例规范
