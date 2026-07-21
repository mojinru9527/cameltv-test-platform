# Batch 26-2 — 知识中心 UX 修复 QA 报告
> **QA (🔍)** | Date: 2026-07-21 | Verdict: READY FOR DEV（验证清单就绪，待 Slice 完成后逐条验证）

## 测试总览

| 维度 | 检查点数 | 覆盖范围 |
|------|---------|---------|
| 弹窗交互 | 8 | ProjectTab / PlatformTab / SourceListTab / ArtifactReviewTab |
| Tab 导航 | 4 | 默认 Tab / 顺序 / URL 参数 |
| 搜索 | 3 | 常驻栏 / 全状态检索 |
| 图谱 | 3 | 域切换 / 数据隔离 |
| 批量操作 | 3 | 批量采纳 / 批量驳回 / 批量导入 |
| 弹窗 UI | 4 | 尺寸 / 文字大小 / Select 对齐 |
| 溯源 | 3 | 模型字段 / 弹窗展示 |
| **总计** | **28** | — |

---

## 逐条件验证

### C1: 项目知识 Tab — 知识源点击弹窗
**变更文件**: [ProjectTab.tsx:73-89](test-platform-v2/frontend/src/pages/knowledge/components/ProjectTab.tsx#L73-L89)
| 检查项 | 方法 | 预期 |
|--------|------|------|
| 点击知识源条目 | 浏览器手动操作 | 弹出 Dialog，显示标题/类型/保鲜评分 |
| 弹窗内容完整性 | 目视检查 | 含原始内容区 + 切片列表 + 元数据网格 |
| 弹窗尺寸 | DevTools 测量 | 宽度 ≥ 90vw，高度 ≥ 85vh |
| 关闭弹窗 | 点击 X / 点击遮罩 / 按 Esc | 弹窗关闭，状态重置 |

### C2: 平台研发 Tab — 分区折叠 + 知识源点击
**变更文件**: [PlatformTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/PlatformTab.tsx)
| 检查项 | 方法 | 预期 |
|--------|------|------|
| 首次加载分区状态 | 刷新页面 | 仅 area 分区展开，其余折叠 |
| 点击折叠分区标题 | 点击 resource 标题 | 该分区展开，图标变 ChevronDown |
| 点击展开分区标题 | 再次点击 | 该分区折叠，图标变 ChevronRight |
| 点击知识源条目 | 点击展开分区内任意条目 | 弹窗打开，内容完整 |
| 弹窗内容与 SourceListTab 一致 | 同一条知识源在两边打开对比 | 内容一致（原始内容+切片+元数据） |

### C3: 概览默认 Tab + Tab 顺序
**变更文件**: [index.tsx:26](test-platform-v2/frontend/src/pages/knowledge/index.tsx#L26)
| 检查项 | 方法 | 预期 |
|--------|------|------|
| 无 URL 参数时默认 Tab | 访问 `/knowledge` | 显示概览仪表盘 |
| Tab 顺序 | 目视检查 Tab 栏 | 概览 → 项目知识 → 平台研发 → … |
| URL 参数覆盖 | 访问 `/knowledge?tab=project` | 显示项目知识（不受默认值影响） |

### C4: 搜索栏常驻 + 全状态检索
**变更文件**: [index.tsx](test-platform-v2/frontend/src/pages/knowledge/index.tsx) + [search_service.py](test-platform-v2/backend/app/services/knowledge/search_service.py)
| 检查项 | 方法 | 预期 |
|--------|------|------|
| 搜索栏在所有 Tab 可见 | 切换每个 Tab | 搜索栏始终在 Tab 栏上方 |
| 搜索回车触发 | 输入关键词 + 回车 | 执行检索并跳转到结果展示 |
| 检索含非 active 切片 | API 测试：搜索已知的 deprecated 切片关键词 | 返回结果中含 deprecated 状态切片 |

### C5: 图谱知识域隔离
**变更文件**: [GraphTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/GraphTab.tsx) + [knowledge.py (api)](test-platform-v2/backend/app/api/v1/knowledge.py#L597)
| 检查项 | 方法 | 预期 |
|--------|------|------|
| 默认显示项目知识域 | 打开图谱 Tab | Toggle 在「项目知识」 |
| 切换域后图谱刷新 | 点击「平台研发」 | 节点/边更新，仅显示平台域实体 |
| 两域数据隔离 | 分别截图对比 | 无交叉（项目域不含 platform_doc 实体） |

### C6: 弹窗尺寸统一 + Select 错位修复
**变更文件**: 各弹窗组件 + [select.tsx](test-platform-v2/frontend/src/components/ui/select.tsx)
| 检查项 | 方法 | 预期 |
|--------|------|------|
| 弹窗最小宽度 | DevTools 测量所有类型弹窗 | ≥ max-w-4xl（896px） |
| 内容文字可读 | 目视 | ≥ text-sm（14px） |
| Select 下拉在弹窗中不错位 | 打开弹窗 → 点 Select | 下拉紧贴触发器，不偏移 |
| 代码区可滚动 | 滚动原始内容/切片 | 滚动流畅，不截断 |

### C7: AI 审核台批量操作
**变更文件**: [ArtifactReviewTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/ArtifactReviewTab.tsx)
| 检查项 | 方法 | 预期 |
|--------|------|------|
| pending 产物批量采纳 | 勾选 3 条 → 批量采纳 | 3 条全变 approved，toast 提示"成功 3 条" |
| pending 产物批量驳回 | 勾选 2 条 → 批量驳回（填原因） | 2 条全变 rejected，toast 提示 |
| approved 产物批量导入 | 勾选 2 条 → 批量导入 | 2 条全变 imported |

### C8: 溯源字段
**变更文件**: [knowledge.py (model)](test-platform-v2/backend/app/models/knowledge.py) + [SourceListTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/SourceListTab.tsx)
| 检查项 | 方法 | 预期 |
|--------|------|------|
| 模型迁移成功 | `alembic upgrade head` | 无报错 |
| 弹窗显示溯源 | 打开任意知识源弹窗 | 元数据区显示 项目 → 模块 → 来源 链路 |
| module_name 自动提取 | 创建新知识源 | ingest 后 module_name 不为空 |

---

## 性能/兼容性

| 检查项 | 方法 | 阈值 |
|--------|------|------|
| TypeScript 编译 | `npx tsc --noEmit` | 0 error |
| Console 报错 | DevTools console | 0 error / 0 warning |
| API 回归 | 运行 15 个知识中心 API 测试 | 全部 200 |
| 弹窗打开延迟 | Performance 面板 | < 500ms |

---

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| — | — | 待 Slice 完成后验证 | — | — |

---

## 发布建议
**状态**: READY FOR DEV — 28 个检查点已就绪，待 Slice 1-7 完成后逐条验证。
