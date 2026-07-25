# Batch 45 — Design Spec
> **Design (🎨)** | Date: 2026-07-26 | Status: 就绪

## 0. 技术体系确认

- **前端**: React 18 + TypeScript + shadcn/ui (Radix + Tailwind + CVA)
- **后端**: FastAPI + SQLAlchemy 2.0 + Alembic + SQLite/PG
- **CSS**: Tailwind + theme-lab.css (5 主题: cyberpunk, xlab, apple, clay, liquid-glass)
- **Token 体系**: CSS 自定义属性 `var(--*)`，语义级 (bg, surface, ink, muted, primary, etc.)

## 1. 组件/模型规格表

### 1.1 WikiDiffItem 字段扩展

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `left_ref` | Text | `""` | 左侧来源引用 (URL/文件名/版本号) |
| `right_ref` | Text | `""` | 右侧来源引用 |
| `left_scope` | Text | `""` | 左侧范围限定 (模块/文件/章节) |
| `right_scope` | Text | `""` | 右侧范围限定 |

现有字段 `left_value`/`right_value` 保持为差异内容本身，新增 4 字段为上下文元数据。

### 1.2 WikiReviewItem 表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int PK | 自增 |
| `task_id` | int FK → wiki_diff_task.id | 所属任务 |
| `item_id` | int FK → wiki_diff_item.id | 被审查差异项 |
| `project_id` | int | 项目隔离 |
| `reviewer` | str(100) | 审查人标识 |
| `decision` | str(20) | accepted / rejected / deferred |
| `reason` | Text | 审查理由 |
| `created_at` | datetime | 审查时间 |

### 1.3 WikiReviewContradiction 表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int PK | 自增 |
| `task_id` | int FK → wiki_diff_task.id | 所属任务 |
| `item_a_id` | int FK → wiki_diff_item.id | 矛盾项 A |
| `item_b_id` | int FK → wiki_diff_item.id | 矛盾项 B |
| `project_id` | int | 项目隔离 |
| `description` | Text | 矛盾描述 |
| `resolution` | Text | 解决方式 |
| `resolved_by` | str(100) | 解决人 |
| `created_at` | datetime | 创建时间 |
| `resolved_at` | datetime | 解决时间 |

## 2. API 设计

### 2.1 lanhu_mcp_enabled Guard

```
GET/POST /api/v1/wiki/lanhu-evidence/*  →  503 if not LANHU_MCP_ENABLED
```

实现方式：新增 `_require_lanhu_mcp_enabled` FastAPI Dependency，复用到所有蓝湖导入端点。

```python
def _require_lanhu_mcp_enabled():
    if not settings.lanhu_mcp_enabled:
        raise HTTPException(status_code=503, detail="蓝湖 MCP 未启用")
    return True
```

### 2.2 Wiki Review 端点

```
POST /api/v1/wiki/diff-tasks/{task_id}/review
  Body: { "items": [{ "item_id": int, "decision": "accepted|rejected|deferred", "reason": str }] }
  → 写入 wiki_review_item 表
  → 返回 201

GET  /api/v1/wiki/diff-tasks/{task_id}/reviews
  → 返回该任务的所有审查记录
```

## 3. CSS 设计规范

### 3.1 ThemeLab token 对齐 (C24-C1)

**走查范围**: theme-lab.css (2927 行)

**发现的 token 偏差** (需要修复):

| 位置 | 当前 | 修改为 | 理由 |
|------|------|--------|------|
| L:289 `color: #edf2f5` | 硬编码 | `var(--ink)` | lab-header 文字色应跟随主题 |
| L:290 `background: #11161c` | 硬编码 | `var(--surface)` | lab-header 背景应跟随主题 |
| L:291 `border-bottom: 1px solid #2d3640` | 硬编码 | `1px solid var(--line-strong)` | 边框色跟随主题 |
| L:345 `color: #96a4b2` | 硬编码 | `var(--muted)` | 副文字色 |
| L:359 `background: #1b222b` | 硬编码 | `var(--surface-soft)` | theme-switcher 背景 |
| L:360 `border: 1px solid #323c48` | 硬编码 | `1px solid var(--line)` | theme-switcher 边框 |
| L:371 `color: #9da9b6` | 硬编码 | `var(--muted-strong)` | switcher button 默认色 |
| L:379 `color: #ffffff` | 硬编码 | `var(--ink-strong)` | switcher hover 色 |
| L:385 `background: #323d4b` | 硬编码 | `var(--primary-soft)` | switcher active 背景 |
| L:389 `color: #788696` | 硬编码 | `var(--muted)` | switcher span |
| L:395 `color: #b8c5d2` | 硬编码 | `var(--muted-strong)` | switcher active span |
| L:403 `color: #9eaab7` | 硬编码 | `var(--muted)` | lab-coverage |
| L:408 `color: #75dfaa` | 硬编码 | `var(--success)` | lab-coverage b |

**注意**: 这些硬编码色值在 `.lab-header` 等 class 中，不随主题切换而变化。将它们改为 `var(--*)` 引用即可让 lab-header 自动适配当前主题。

### 3.2 Liquid Glass morphing 背景 (C24-C2)

**目标**: MainLayout 在 liquid-glass 主题下激活动态 morphing 背景。

**设计**:
```css
.lg-morph-bg {
  position: relative;
  isolation: isolate;
}

.lg-morph-bg::before {
  content: '';
  position: fixed;
  inset: 0;
  z-index: -1;
  background:
    radial-gradient(circle at 30% 20%, rgba(124, 92, 231, 0.12) 0%, transparent 35%),
    radial-gradient(circle at 70% 60%, rgba(78, 240, 184, 0.08) 0%, transparent 30%),
    radial-gradient(circle at 50% 80%, rgba(78, 240, 232, 0.06) 0%, transparent 25%);
  animation: morph-shift 20s ease-in-out infinite alternate;
}

@keyframes morph-shift {
  0% { transform: scale(1) rotate(0deg); }
  100% { transform: scale(1.08) rotate(2deg); }
}
```

**集成点**: MainLayout.tsx L:279 `<SidebarInset>` — 在 liquid-glass 主题时添加 `lg-morph-bg` class。

**触发方式**: 通过 `useTheme()` 的 `colorTheme` 状态，当 `colorTheme === 'liquid-glass'` 时应用。

## 4. 设计 QA 走查发现

### 🔵 P3-01: lab-header 硬编码颜色破坏主题一致性
[theme-lab.css:289-291](test-platform-v2/frontend/src/theme-lab/theme-lab.css#L289-L291) — lab-header 使用硬编码 `#edf2f5` / `#11161c` / `#2d3640`，在 apple/clay 亮色主题下产生不协调的暗色 header。
**建议**: Task 2.1 中替换为 `var(--*)` token。

### 🔵 P3-02: theme-switcher 在非暗色主题下可见性问题
[theme-lab.css:359-396](test-platform-v2/frontend/src/theme-lab/theme-lab.css#L359-L396) — theme-switcher 硬编码暗色背景 `#1b222b`，在亮色主题下过于突兀。
**建议**: 同上，替换为 token 引用。

### ⚪ P4-01: MainLayout header glass-card 无实际 glass 效果
[MainLayout.tsx:281](test-platform-v2/frontend/src/layouts/MainLayout.tsx#L281) — `glass-card` class 存在但未在 theme-lab.css 中定义任何 glass 相关样式。
**建议**: Task 2.2 中一并修复。

## 5. 设计签核

**结论**: 通过 — 本批次以代码级对齐为主，无新增 UI 组件，风险可控。
