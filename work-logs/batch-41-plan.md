# Batch 41 — 功能计划 (Feature Plan)

> **批次**: batch-41 | **日期**: 2026-07-24 | **状态**: Draft
> **来源**: C-CONDITIONS Open 项 + 改进任务 Backlog + batch-37 Non-goals

## v40 验收结果回顾

| 状态 | 数量 | 说明 |
|------|------|------|
| ✅ PASS | 10 | 所有核心页面渲染正确，功能可用 |
| ⚠️ WARN | 2 | 数据空白（无需求/AI用例数据，非功能缺陷） |
| ❌ FAIL | 0 | 无功能故障 |

**v40 已交付**: 平台初版完整 → 需求管理 + AI用例生成 + 用例服务 + 测试计划 + 报告中心 + 发布包(B4+B5) + 模块联动(B6) + 蓝湖设置(A7) + 评审流(A6)

---

## 1. v41 目标

从 **"功能完整"** 走向 **"生产可信"**. v40 完成了功能拼图，v41 聚焦安全和质量基线:

1. **安全加固 (P0)**: JWT Cookie 安全 + XSS 防护
2. **C-CONDITIONS P1 清偿**: 补单测 + UI 编译链路 + Knowledge Sphere 指标达标
3. **真实执行引擎稳定化**: API 测试生产保护 + UI 自动化产物回看

---

## 2. Epic 分解

### Epic 1: 安全加固 — JWT httpOnly Cookie (S1) `P0`

**来源**: Backlog Epic S1, T0 优先级

| Slice | 内容 | 工作量 |
|-------|------|--------|
| S1a | 后端 `Set-Cookie` 配置 (httpOnly/Secure/SameSite) | 4h |
| S1b | 后端 Cookie 读取认证（优先 Cookie, fallback Authorization header） | 3h |
| S1c | 前端移除 localStorage token, Axios 拦截器 `withCredentials: true` | 4h |
| S1d | `/auth/logout` 清除 Cookie | 1h |
| S1e | 联调测试 + Cookie 安全回归 | 3h |

**总预估**: 15h

---

### Epic 2: 安全加固 — XSS 防护 (S2) `P0`

**来源**: Backlog Epic S2, T0 优先级

| Slice | 内容 | 工作量 |
|-------|------|--------|
| S2a | 前端 `dangerouslySetInnerHTML` 审计与替换 | 4h |
| S2b | 后端 CSP header 配置 (`csp_header` 已存在, 需审计规则) | 2h |
| S2c | 后端输出编码审计 (响应 JSON 中无未转义 HTML) | 2h |
| S2d | 安全验证 (XSS payload 测试) | 2h |

**总预估**: 10h

---

### Epic 3: C-CONDITIONS P1 清偿 `P1`

**来源**: C-CONDITIONS.md Open 项

| Slice | ID | 内容 | 工作量 |
|-------|-----|------|--------|
| S3a | C21-P1-2 | 补三个服务单测: failure_analyzer / report_aggregator / task_worker | 8h |
| S3b | C22-C2 | 第一条成功编译链路 (P0 功能用例→可执行 .spec.ts→headless Chromium→截图) | 8h |
| S3c | C22-C3 | 统一编排器批量执行 (3 API + 3 功能→6/6 有结果→报告自动生成) | 6h |
| S3d | C21-P1-3 | `现状功能PRD.md` 模块 11/12 详情段同步为真实实现描述 | 2h |
| S3e | C27-C1 | 模块树自动提取准确率 ≥70% (staging 验证) | 4h |

**总预估**: 28h

---

### Epic 4: API 测试生产保护 (batch-37 非目标补位) `P0`

**来源**: batch-37 PRD Epic 2, batch-34 验收报告 P0 阻断项

| Slice | 内容 | 工作量 |
|-------|------|--------|
| S4a | 环境标记: 每个 Environment 增加 `is_production` 字段 + UI 标记 | 4h |
| S4b | 执行前拦截: 生产环境 API 测试弹出二次确认 + 审批记录 | 3h |
| S4c | API 执行结果保存完整 request/response 快照 | 5h |

**总预估**: 12h

---

### Epic 5: UI 自动化产物回看 (batch-37 非目标补位) `P0`

**来源**: batch-37 PRD Epic 3, batch-34 验收报告 P0 阻断项

| Slice | 内容 | 工作量 |
|-------|------|--------|
| S5a | 截图缩略图展示 (执行结果详情页) | 3h |
| S5b | 视频在线播放 (HTML5 video) | 2h |
| S5c | trace 文件下载/Playwright Trace Viewer 引导 | 2h |
| S5d | UI 测试异步执行 + 环境变量注入 | 5h |

**总预估**: 12h

---

## 3. 优先级排序

```
批次 41-1 (Week 1): Epic 1 (S1 JWT Cookie) + Epic 2 (S2 XSS)
  → 安全基线补齐, 消除 XSS→账户接管攻击面

批次 41-2 (Week 2): Epic 4 (API 生产保护) + Epic 5 (UI 产物回看)
  → P0 阻断项修复, 平台可投入生产测试

批次 41-3 (Week 3): Epic 3 (C-CONDITIONS P1 清偿)
  → 质量基线达标, 技术债务清理
```

---

## 4. 非目标 (本次不做)

- **S3 RBAC 权限补齐**: 当前基础 RBAC 已可用, 细粒度权限放在 v42
- **S4 BackgroundTasks 可靠性**: 依赖 S1 完成后启动, v42
- **S5 SMTP 安全 / S6 文件上传安全**: v42
- **S7 三态统一 / S8 WCAG 无障碍**: v42 前端体验优化批次
- **音视频 ffprobe 真实化 (batch-37 Epic 1)**: 需服务端安装 ffmpeg 依赖, 作为 v42 P0
- **Swagger 导入自动生成接口用例 (batch-37 Epic 4)**: v42
- **批量执行 + 执行指派 (batch-37 Epic 5)**: v42
- **报告 PDF/Excel 导出 (batch-37 Epic 6)**: v42
- **C-CONDITIONS P2/P3 项**: 不阻塞生产化, 择机归档或延期

---

## 5. 成功指标

| 指标 | 当前基线 | v41 目标 |
|------|---------|---------|
| JWT 存储方式 | localStorage (XSS 可读) | httpOnly Cookie (XSS 不可读) |
| innerHTML/dangerouslySetInnerHTML | 未审计 | 0 处未消毒的 HTML 注入 |
| P0 安全缺陷 | 2 (P1-1, P1-2) | 0 |
| 核心服务单测覆盖 | 缺失 3 个服务 | 3 服务均有 P0 路径单测 |
| UI 编译链路 | 0 条可执行 | 1 条端到端可执行 |
| API 生产保护 | 无保护 | 生产环境标记 + 二次确认 |
| UI 产物回看率 | 0% | 100% (截图+视频可查看) |

---

## 6. 依赖与风险

| 依赖/风险 | 影响 | 对策 |
|----------|------|------|
| httpOnly Cookie 要求前端 `withCredentials` 适配 CORS | CORS 配置需同步更新 | S1e 联调阶段验证 |
| CSP header 可能阻断现有内联脚本 | 页面功能异常 | 逐页回归测试 |
| failure_analyzer 等 3 服务可能依赖外部 API | 单测需要 mock | 使用 pytest monkeypatch |
| UI 编译链路依赖 Playwright 执行器 | 需 Playwright 环境 | 已有 playwright-executor 基础设施 |

---

## 7. 已关闭 C-CONDITIONS (v40)

v40 完成了以下 C-CONDITIONS:

| ID | 内容 | 方式 |
|----|------|------|
| A7 | Lanhu 设置对话框双端配置 | 蓝湖设置 Dialog 双端字段已实现 |
| B2 | AiResultModal 三 Tab (功能/接口/UI) | 前端 AiResultModal.tsx 重构完成 |
| B4+B5 | 发布包回归范围 + 触发 UI 回归 | Release bundles 页面 + BundleDetail 实现 |
| B6 | 模块联动追踪页面 | Integration 页面实现 |
| A6 | 用例评审流 (提交/通过/驳回) | 前端 review 按钮已实现 |
| C21-P1-1 | apitest create_task 500 修复 | 已合入 |

---

*本计划基于 batch-34 Leader 审查、batch-37 PRD 非目标、C-CONDITIONS Open 项和 Backlog 安全基线编写。关联文件: [C-CONDITIONS.md](../C-CONDITIONS.md), [改进任务backlog.md](../test-platform-v2/docs/改进任务backlog.md), [batch-37 PRD](../work-logs/batch-37-platform-ga-production-readiness-prd-summary.md)*
