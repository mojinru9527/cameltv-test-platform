---
title: "CamelTv 文档标准"
owner: "qa-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2027-06-26"
tags: ["standards", "documentation", "frontmatter", "freshness"]
related: ["adr/README.md", "adr/template.md"]
---

# CamelTv 文档标准

> 项目内所有 Markdown 文档的元数据和编写规范。

## 1. Frontmatter 元数据

每个 Markdown 文档（CLAUDE.md / README / PRD / 设计方案 / ADR）**头部**需包含 YAML frontmatter。

### 1.1 字段定义

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `title` | ✅ | string | 文档标题（简洁，用中文） |
| `owner` | ✅ | string | 负责人/团队（可用 `backend-team` / `frontend-team` / `qa-team`） |
| `last_reviewed` | ✅ | date (YYYY-MM-DD) | 最后审核日期 |
| `status` | ✅ | enum | `active`（活跃）\| `draft`（草稿）\| `deprecated`（已废弃）\| `archived`（归档） |
| `expires` | ❌ | date (YYYY-MM-DD) | 预计过期日期（超过后需审核是否仍有效） |
| `tags` | ❌ | string[] | 标签（用于分类和搜索） |
| `related` | ❌ | string[] | 关联文档路径 |

### 1.2 模板

```yaml
---
title: "文档标题"
owner: "backend-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2026-12-26"
tags: ["fastapi", "backend", "architecture"]
related: ["docs/adr/0001-use-python-fastapi-monostack.md"]
---
```

### 1.3 状态生命周期

```
draft → active → deprecated → archived
  │                  │
  └──────────────────┘  (可直接废弃)
```

- **draft**：写作中，未定稿，不强制执行保鲜规则
- **active**：现行有效，需遵守保鲜规则（不超过 `expires` 日期）
- **deprecated**：已被替代或不再适用，保留 3 个月后归档
- **archived**：历史文档，仅供查阅，不再维护

## 2. 文档命名

| 类型 | 命名格式 | 示例 |
|------|----------|------|
| CLAUDE.md | 固定名称 | `CLAUDE.md` |
| README | 固定名称 | `README.md` |
| ADR | `NNNN-{slug}.md` | `0001-use-python-fastapi-monostack.md` |
| 设计方案 | `{主题}-{类型}.md` | `测试平台-前后端分离重构方案.md` |
| PRD | `{产品}-{类型}PRD.md` | `CamelTv测试平台-完整PRD.md` |
| 接入指南 | `{动词}.md` | `onboarding.md` |
| 命令速查 | `COMMANDS.md` | 固定名称 |

## 3. 内容规范

### 3.1 标题层级

- `#` 文档标题（每个文件只有一个）
- `##` 章节标题
- `###` 子章节
- `####` 最小标题

### 3.2 代码块

```markdown
​```language
code here
​```
```

- 必须标注语言（`python` / `bash` / `typescript` / `json` / `yaml`）
- Shell 命令标注平台差异：`# Windows` / `# macOS / Linux`

### 3.3 表格

- 关键信息优先使用表格（环境列表、版本对比、API 列表）
- 表格必须有表头

### 3.4 链接

- 内部链接使用相对路径：`[text](../path/to/file.md)`
- 外部链接使用完整 URL：`[text](https://...)`
- 代码引用使用文件路径 + 行号：`[file.py:42](../path/file.py#L42)`

## 4. 文档保鲜

### 4.1 审核周期

| 文档类型 | 默认 expires（月） | 审核人 |
|----------|-------------------|--------|
| CLAUDE.md | 6 | owner |
| ADR | 12 | Tech Lead |
| README | 6 | owner |
| PRD | 与产品版本绑定 | PM |
| Runbook/运维文档 | 3 | 运维 |
| 设计方案 | 项目结束即 deprecated | 作者 |

### 4.2 自动化检查

每月 1 日 CI 运行 `scripts/check_doc_freshness.py`，检查所有 `active` 文档：
- `last_reviewed` 距今 > 设定周期 → 告警
- `expires` 已过期 → 告警
- `status: deprecated` 超过 3 个月 → 提醒归档

## 5. 适用范围

以下文件需遵循本标准（新文件必须，存量逐步改造）：
- `CLAUDE.md`（所有层级）
- `README.md`（所有模块）
- `docs/` 下的所有 `.md` 文件
- `tests/` 下的 `README.md`

以下文件可选遵循：
- Memory 文件（已在 frontmatter 中，格式不同）
- 测试用例 Markdown（有自己的模板）
