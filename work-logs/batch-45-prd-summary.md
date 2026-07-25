# Batch 45 — PRD Summary
> **Product (🟦)** | Date: 2026-07-26 | Status: Draft

## 1. 问题陈述

batch-44 已将 5 个 P1–P3 C-conditions 归位（C21-P1-3, C21-P2, C21-P3, B19-C1, B21-C2），commit `66018ef` 已推送远端 `feature/batch-44`。当前 C-CONDITIONS.md 剩余 **23 Open** 条件，其中：

- **7 个 blocked**：Docker (C43-1, C43-2, C44-C1, C44-C4)、人工审查 (C31-2)、物理设备 (CP-C1, CP-C2)
- **1 个 semi-blocked**：TPv2-B19-C2（需 `npm install` 后才能跑 vitest）
- **2 个重复**：batch-18-C7 与 C21-P1-5 同为 "迁移 20260710_0017 staging 双向演练"

扣除 blocked/重复后，**实际可执行 13 个条件**，全部为 P2/P3 优先级（除 C22-C2/C3 为 P1 但依赖 Playwright 基础设施已就绪）。

**用户痛点**：
- 6 个 batch-18 遗留项（C6/C7/C8/C9/C11/C14）自 2026-07-10 起 Open 已 16 天，属于 Wiki Diff 模块的技术债
- ThemeLab 主题系统（C24-C1/C2/C3）CSS token 与实际组件未完全对齐，视觉回归无自动化
- 知识中心 UX（C26KB-C1/C2）弹窗尺寸与图谱数据隔离未经正式走查
- 用例服务布局（C25v2-C2）固定高度布局的响应式表现未验证
- C22 Playground（C22-C2/C3）端到端编译链路仍为 P1 未闭合

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| C-CONDITIONS Open 数 | 23 | ≤15 | 本 batch 结束 |
| batch-18 遗留项清理 | 6 Open | ≤3 Open | 本 batch 结束 |
| ThemeLab 设计走查缺陷 | 未知 | 发现并修复 ≥3 项 | 本 batch 结束 |
| 后端测试通过率 | 757 pass | 保持 757+ | CI |
| 前端 typecheck+build | 未验证 | 通过 | 本 batch 结束 |

## 3. 非目标（本次不做）

- **Docker 相关**：C43-1 (Alembic staging), C43-2 (Tier 1 browser), C44-C1 (module tree ground truth), C44-C4 (release_bundle staging) — blocked on Docker 环境
- **人工审查**：C31-2 — 需真实人类 reviewer
- **物理设备**：CP-C1 (Android), CP-C2 (iOS) — 需真机
- **C22-C2/C3 Playground 完整实现**：P1 但工作量 > 本 batch 范围，仅做代码级可行性评估和接口设计
- **TPv2-B19-C2 contract drift**：blocked on `node_modules` 安装，若本 batch 中 npm install 成功则纳入

## 4. 用户故事 + 验收标准

### Slice 1：batch-18 遗留项批量归位（P2/P3）

**US-1**: As a 平台管理员, I want lanhu_mcp 导入在 lanhu_mcp_enabled=False 时被拒绝, so that 未启用的功能不会产生脏数据。
- Given lanhu_mcp_enabled=False / When 调用蓝湖导入 API / Then 返回 503 错误 + 明确提示

**US-2**: As a API 消费者, I want wiki diff 接口返回 left/right 独立的 ref 和 scope 字段, so that 调用方无需二次查询即可获得完整差异上下文。
- Given 一次 wiki diff 查询 / When 请求 diff 结果 / Then 每个差异项包含 left_ref, right_ref, left_scope, right_scope

**US-3**: As a 平台开发者, I want review_items 和 contradictions 持久化到独立表, so that 审查历史可追溯、可审计。
- Given wiki diff 审查完成 / When 确认审查结果 / Then review_items 写入 wiki_review_item 表

**US-4**: As a 质量工程师, I want 标注语料评估差异召回率/误报率的 baseline, so that diff classifier 质量可量化。
- Given 标注语料集 / When 运行评估脚本 / Then 输出召回率和误报率

**US-5**: As a 运维人员, I want 20260710_0017 迁移的 staging 双向演练文档, so that 生产部署前有可复现的验证步骤。
- Given 0017 迁移脚本 / When 按文档执行 upgrade→downgrade→upgrade / Then 数据库状态一致

**US-6**: As a 运维人员, I want 分环境灰度放量 SOP 文档, so that 新功能上线风险可控。
- Given SOP 文档 / When 按文档操作 / Then 可在 test→staging→prod 逐级放量

### Slice 2：ThemeLab 主题系统对齐（P2）

**US-7**: As a 设计师, I want theme-lab.css 深层组件样式匹配新视觉 token, so that 5 套主题的组件表现一致。
- Given theme-lab.css 更新 / When 切换 5 套主题 / Then 深层组件（dropdown, dialog, tooltip）样式匹配对应 token

**US-8**: As a 用户, I want MainLayout 集成 .lg-morph-bg class, so that Liquid Glass morphing 背景效果在所有主题下正确渲染。
- Given MainLayout 渲染 / When 切换主题 / Then .lg-morph-bg 动画流畅、颜色匹配当前主题

### Slice 3：布局与 UX 走查（P2）

**US-9**: As a 用户, I want 用例管理页固定高度布局在 Desktop/Tablet 分辨率下正确显示, so that 不会出现内容截断或过度滚动。
- Given 用例管理页 / When 在 1920×1080 和 1024×768 分辨率查看 / Then 内容区域高度正确、无溢出

**US-10**: As a 用户, I want 知识中心弹窗尺寸符合设计规范, so that 长内容不会被截断。
- Given 知识中心弹窗 / When 打开各类型弹窗 / Then 弹窗尺寸 ≥ 设计稿最小尺寸、内容完整可见

**US-11**: As a 管理员, I want 图谱两域（蓝湖 + 平台）数据隔离可确认, so that 避免跨域数据泄漏。
- Given 图谱视图 / When 切换蓝湖域和平台域 / Then 两域节点/边数据无交叉

## 5. 技术考量

| 依赖 | 状态 | 风险 |
|------|------|------|
| batch-44 PR 未合入 main | feature/batch-44 已推送, 未创建 PR | 低: batch-45 从 main 切出, 独立 worktree |
| lanhu_mcp_enabled 配置 | `backend/app/core/config.py` 已有 LANHU_MCP_ENABLED | 低: 只需在导入端点加 guard |
| Wiki 模型 | `backend/app/models/wiki.py` 已有 WikiPage, WikiDiff 等 | 中: 新表需 Alembic 迁移 |
| ThemeLab CSS | `frontend/src/` theme-lab.css 存在 | 低: CSS 改动 |
| Playwright 基础设施 | `backend/app/services/playwright_executor.py` 已就绪 | C22 仅评估 |
| node_modules 缺失 | 前端 `node_modules` 未安装 | 高风险: 阻断所有前端验证 |

### node_modules 风险应对

本 batch 第一步先尝试 `npm ci` 安装依赖。如果失败（网络/权限），则：
- 仅执行不依赖前端的后端代码任务（Slice 1 全部 + Slice 4）
- 前端走查类条件（Slice 2/3）降级为代码级审查而非运行时验证
- 工件中明确记录限制

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 代码交付 | Dev | 后端 757+ 测试通过 |
| 前端 build | Dev | typecheck + build 通过（若 npm install 成功） |
| PR Review | Leader | C-CONDITIONS 更新 + 工件齐全 |
| 合入 | main | Squash merge feature/batch-45 → main |
