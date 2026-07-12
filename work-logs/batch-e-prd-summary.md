# 批次 E (Sprint 0.6) -- PRD 摘要

> **产品经理**: Agent Team Product Department
> **日期**: 2026-07-01
> **状态**: 范围已确认，待开发部门实施
> **前置批次**: 批次 A (PR #4) + 批次 B (PR #5) + 批次 C (PR #6) + 批次 D (PR #7) -- 均已合并 develop

---

## 1. 产品背景：为什么这批至关重要

批次 E 是 P1 安全基线 Sprint 的**收尾批次**，也是 V2.2 "信任补齐" 阶段的最终交付。前四批 (A-D) 已覆盖 8 项安全/可靠性/体验改进，从 JWT Cookie 安全到 WCAG 无障碍，共计 35 个切片、累计改动 130+ 文件。然而，以下四个缺口必须在 V2.2 发布前关闭：

1. **useApi 在 React 18 Strict Mode 下的健壮性缺口**（C5）：开发模式下双挂载 (double-mount) 可能导致永久 loading，影响开发者体验和调试效率。
2. **DataTable 与 AsyncState 集成模式未文档化**（C6）：批次 D 引入的 AsyncState 模式与既有 DataTable 页面使用不同的错误处理策略，团队需要清晰的模式指引。
3. **无障碍基础设施未经过运行时验证**（C7）：S8a-d 建立了色彩对比度 token、键盘导航、aria-label 模式和 focus trap hook，但 S8e "全平台 axe-core 扫描零 violation" 的 AC 尚未执行运行时验证。
4. **P1 安全修复缺乏回归测试套件**（C8）：批次 A-D 累计 8 大安全修复（JWT Cookie、XSS、CSRF、CSP、RBAC、SMTP TLS、流式上传、安全头），缺乏统一的回归测试套件来保障后续迭代不引入安全退化。

**如果跳过批次 E**：V2.2 安全基线存在未验证的盲区——运行时验证缺失、开发者体验有坑、安全修复无回归保护。

## 2. 成功指标

| # | 指标 | 目标 | 测量方式 |
|---|------|------|----------|
| 1 | Strict Mode 稳定性 | useApi 在 React 18 Strict Mode 下无永久 loading | 浏览器 DevTools 验证：双挂载后状态正确恢复 |
| 2 | 模式文档覆盖率 | DataTable 和 AsyncState 两种模式均有代码示例 | 文档审查：2 种模式 x 最少 1 个完整示例 |
| 3 | axe-core 违规数 | 全 12 页面 0 violation | `npx axe --stdout` 扫描全部页面 |
| 4 | Lighthouse 无障碍评分 | 核心页面 >= 90 分 | CI `lighthouse --only-categories=accessibility` |
| 5 | 安全回归测试覆盖 | 8 项 P1 修复均有对应测试用例 | 测试套件审查：8 个测试类/模块 |
| 6 | 安全回归通过率 | 100% | `pytest` 安全测试套件全部通过 |

## 3. 范围定义

### 纳入范围 (4 Leader Conditions, 8 切片估算)

| # | 任务 | 优先级 | 模块 | 说明 |
|---|------|--------|------|------|
| C5 | useApi Strict Mode 健壮性 | LOW | frontend | useEffect cleanup 重启 fetch，消除永久 loading |
| C6 | DataTable + AsyncState 集成模式文档 | LOW | docs | 两种错误处理模式文档化 + 代码示例 |
| C7 | 全平台无障碍审计 | MEDIUM | frontend | 12 页面 axe-core/Lighthouse 运行时扫描 + 违规修复 |
| C8 | P1 安全回归测试套件 | HIGH | backend/test | 8 大安全修复的端到端/单元测试覆盖 |

**预估工时**: ~20h | **模块**: 前端 (8h) + 测试 (8h) + 文档 (4h)

### 排除范围

| 项目 | 原因 |
|------|------|
| 新功能开发 | 批次 E 为纯收尾/加固，不引入新功能 |
| 性能优化 | 性能问题不在 P1 安全基线范围内 |
| WCAG AAA 级别 | 已在批次 D 明确排除，属后续迭代 |
| 生产环境渗透测试 | 本次仅限自动化回归测试，人工渗透测试在 V2.2 发布后执行 |
| DataTableAsyncState 开发 | C6 优先文档化现有模式，复合组件开发为可选扩展 |

---

## 4. 用户故事与验收标准

### C5 -- useApi Strict Mode 健壮性

**用户故事**: 作为前端开发者，我在 React 18 Strict Mode (开发模式) 下使用 `useApi` hook 时，即使组件被 React 双挂载 (mount -> unmount -> mount)，数据请求也能正常完成并展示结果，不会卡在永久 loading 状态。

**问题描述**: React 18 Strict Mode 在开发环境下会对组件执行 mount -> unmount -> mount 流程以检测副作用问题。当前 `useApi` 在 unmount 时通过 AbortController 取消请求，但 re-mount 时不会自动重新发起请求，导致进入永久 loading 状态。这在开发调试时造成困扰——开发者必须手动刷新页面或关闭 Strict Mode。

**核心 AC**:
- [ ] `useApi` 在组件首次挂载和 Strict Mode 重新挂载时均正确发起数据请求
- [ ] useEffect cleanup 函数取消当前请求后，re-mount 的 useEffect 启动新请求
- [ ] 验证方式：开发模式 (StrictMode 开启) 下，工作台页面首次加载正常展示数据（不卡 loading）
- [ ] `isRefetching` 状态在 Strict Mode 双挂载场景下正确反映"正在重新请求"
- [ ] 不引入新的内存泄漏：cleanup 中取消的请求不应触发 setState
- [ ] 可选：添加 `useApi` 内部重试机制——请求失败时自动重试 1 次（延迟 1s），作为网络抖动的容错

**预估工时**: 3h

---

### C6 -- DataTable + AsyncState 集成模式文档

**用户故事**: 作为新加入团队的开发者，当我需要创建一个数据列表页面时，我能快速找到两种推荐模式的文档——使用 `<AsyncState>` 包裹的简单页面模式，和使用 `DataTable` 的复杂列表页面模式——并理解每种模式在 loading / error / empty 态下的正确处理方式，避免重复踩坑。

**问题描述**: 批次 D 引入 `useApi` + `AsyncState` 后，平台存在两种数据展示模式：
- **AsyncState 模式**（如工作台、系统管理、质量追溯）：`useApi` + `<AsyncState>` 容器自动管理四态
- **DataTable 模式**（如用例管理、测试计划、报告中心、项目管理）：手动管理分页/筛选/排序状态 + 表格内置 loading/empty

两种模式在错误处理上存在差异：AsyncState 统一通过 ErrorState 组件展示错误+重试；DataTable 页面各自实现错误处理（部分页面直接 toast 后无重试入口）。新开发者面对两种模式容易困惑。

**核心 AC**:
- [ ] 在 `frontend/src/hooks/useApi.ts` 文件顶部 JSDoc 中补充完整的使用示例
- [ ] 在 `frontend/src/components/state/` 目录下创建 `README.md`（或项目级文档），包含：
  - 模式一：简单页面（同步加载列表/统计）—— 使用 `useApi` + `<AsyncState>` 包裹
  - 模式二：DataTable 页面（带分页/筛选/排序）—— 在 DataTable 外层用 ErrorState 包裹，DataTable 内置 loading/empty
  - 每种模式至少 1 个完整代码示例（含 loading/error/empty/data 四种状态的渲染）
- [ ] 文档说明何时选择哪种模式：单次请求无分页 -> AsyncState；需要分页/筛选/排序 -> DataTable 手动管理 + ErrorState 包裹
- [ ] 可选：若团队认同，创建 `DataTableAsyncState` 复合组件，自动组合 DataTable + ErrorState + 分页状态管理

**预估工时**: 4h

---

### C7 -- 全平台无障碍审计

**用户故事**: 作为平台用户（包含使用屏幕阅读器或键盘导航的用户），我在访问平台任何页面时，都能获得一致的无障碍体验——色彩对比度达标、键盘可达所有交互元素、屏幕阅读器能正确播报按钮和表单标签。

**问题描述**: 批次 D 的 S8e "全平台覆盖" 虽然作为 Epic 切片定义，但实际交付 (PR #7) 仅完成了基础设施层 (S8a-d: 色彩 token、键盘 focus-visible CSS、aria-label 模式、focus trap hook)。12 页面的 axe-core 运行时扫描和违规修复尚未执行。若不补齐，S8e 定义的 AC "全平台所有页面通过 axe-core 扫描零 violation" 实际未达成。

**纳入页面** (12 页):

| 页面 | 路由 | 审计重点 |
|------|------|----------|
| 登录 | `/login` | 表单 label 关联、错误 aria-describedby |
| 工作台 | `/workbench` | 图表可访问性、统计卡片 |
| 用例管理 | `/testcase` | DataTable 键盘导航、批量操作按钮 aria-label |
| 测试计划 | `/testplan` | 执行按钮状态、筛选控件 |
| 需求管理 | `/requirement` | AI 生成结果区域、文件上传 |
| 报告中心 | `/report` | 导出按钮、表格 |
| 缺陷管理 | `/defect` | 状态流转表单、附件上传 |
| 项目管理 | `/project` | 成员列表、主题选择 |
| 系统管理 | `/system` | 用户/角色表格、审计日志 |
| 定时任务 | `/schedule` | Cron 表达式输入 |
| 质量追溯 | `/trace` | 矩阵表格、覆盖率色阶信息传达 |
| 脑图视图 | `/mindmap` | 列表视图切换按钮 (键盘替代) |

**核心 AC**:
- [ ] 对上述 12 个页面逐一运行 `npx axe --stdout`，记录违规列表
- [ ] 修复所有 detectable violations（色彩对比度、aria-label 缺失、form label 缺失、heading 层级跳级等）
- [ ] 修复后重新扫描，确认 12 页面均 0 violation
- [ ] 对工作台、用例管理、测试计划 3 个核心页面运行 Lighthouse accessibility audit，评分 >= 90
- [ ] 每个页面修复后截图留档（共 12 张）
- [ ] 人工键盘验收：Tab 遍历核心页面（登录 -> 工作台 -> 用例列表 -> 用例详情），验证焦点顺序合理、无键盘陷阱
- [ ] 若某些 axe 规则无法自动修复（如 `color-contrast` 涉及第三方组件、`heading-order` 结构性改动过大），在文档中记录豁免清单和后续计划

**预估工时**: 8h

---

### C8 -- P1 安全回归测试套件

**用户故事**: 作为平台维护者，当我在后续迭代中修改认证、文件上传、通知发送等模块时，现有的安全回归测试套件能自动检测我是否破坏了任何 P1 安全修复，避免安全退化。

**问题描述**: 批次 A-D 累计 8 项安全修复，每项修复仅在其所在批次编写了单元测试，且测试分散在不同文件中。缺乏一个统一的、可独立运行的安全回归测试套件。后续重构或依赖升级时，没有机制确保安全基线不被破坏。

**覆盖范围** (8 大安全修复):

| # | 安全修复 | 来源批次 | 测试类型 | 关键验证点 |
|---|----------|----------|----------|-----------|
| 1 | JWT httpOnly Cookie | 批次 A | 集成测试 | Cookie 属性 (httpOnly/Secure/SameSite)、header 兼容、登出清除 |
| 2 | XSS innerHTML 修复 | 批次 A | 单元测试 | 脑图 fallback 使用 textContent、恶意 payload 不执行脚本 |
| 3 | CSRF 中间件 | 批次 B | 集成测试 | Origin 头校验、写操作拒绝、API Token 路径豁免 |
| 4 | CSP 响应头 | 批次 B | 集成测试 | script-src 白名单、markmap CDN 放行、inline script 阻止 |
| 5 | RBAC 权限补齐 | 批次 B | 集成测试 | Token/Notify 端点鉴权拒绝、admin 角色权限、非管理员隐藏入口 |
| 6 | SMTP TLS 证书验证 | 批次 C | 单元测试 | 自签证书拒绝、CA bundle 生效、verify_cert=False 降级 warning |
| 7 | 流式上传安全 | 批次 C | 集成测试 | Content-Length 超限 413、文件分块写入、内存增量 < 10MB |
| 8 | OWASP 安全标准头 | 批次 D | 集成测试 | X-Content-Type-Options、X-Frame-Options、Referrer-Policy 头存在 |

**核心 AC**:
- [ ] 创建统一的安全回归测试目录 `backend/tests/security/`（或 `backend/tests/test_security_regression.py`）
- [ ] 每个安全修复至少 1 个正向测试 (修复生效) + 1 个负向测试 (攻击向量被阻止)
- [ ] 测试套件可独立运行：`pytest backend/tests/security/ -v` 全部通过
- [ ] 测试覆盖前端关键安全点：XSS payload 注入 -> 页面不执行脚本 (可用 Playwright 或 jsdom)
- [ ] CI 配置：安全回归测试在每次 PR 时自动运行，失败即阻塞合并
- [ ] 测试数据隔离：使用独立测试 fixtures，不依赖生产/开发数据库
- [ ] 文档化：每个测试类包含 docstring 说明对应安全修复的 PR/Commit 引用

**预估工时**: 8h

---

## 5. 依赖关系

```
C5 (useApi Strict Mode) ── 独立，无依赖，可最先启动
C6 (模式文档)           ── 依赖批次 D 交付物 (useApi + AsyncState 已存在)，无实施依赖
C7 (无障碍审计)         ── 依赖批次 D S8a-d 基础设施，依赖 C5 (Strict Mode 修复后页面才能正常加载扫描)
C8 (安全回归测试)       ── 依赖批次 A-D 全部安全修复已合并 develop，独立可启动
```

**关键路径**: C5 (3h) -> C7 (8h)，总工时约 11h。C6 和 C8 与前端工作并行，无阻塞。

## 6. 实施策略

### 推荐顺序

**Day 1 -- 前端的快速修复 + 文档 + 测试启动**

1. **C5** (3h)：修复 `useApi` Strict Mode 健壮性——改动范围小 (`useApi.ts` 单个文件)，影响面可控，可快速交付。
2. **C6** (4h)：编写模式文档——纯文档工作，可在 C5 验证期间并行进行。
3. **C8 测试骨架** (2h)：搭建安全回归测试目录结构、编写前 4 项测试（JWT Cookie + XSS + CSRF + CSP）。

**Day 2 -- 无障碍审计执行**

4. **C7** (8h)：全平台 12 页面 axe-core 扫描 + 违规修复 + 截图留档。最耗时的任务，建议整天专注。

**Day 3 -- 安全测试收尾 + 最终验证**

5. **C8 收尾** (6h)：完成后 4 项测试（RBAC + SMTP TLS + 流式上传 + 安全头）+ 集成到 CI。
6. **最终回归** (2h)：C5 修复后回归 12 页面正常加载 + C7 扫描零违规验证 + C8 安全测试全绿。

### 并行策略

```
Day 1:  C5 ──────┐
        C6 ──────┤ (并行，纯文档)
        C8 骨架 ──┤ (并行，后端测试)
                  │
Day 2:  C7 ──────┤ (依赖 C5 完成，确保页面正常加载)
        C8 续 ───┤ (并行，与 C7 不同关注面)
                  │
Day 3:  C8 收尾 ──┤
        最终验证 ──┘
```

## 7. 风险与不确定性

| 风险 | 等级 | 概率 | 影响 | 缓解措施 |
|------|------|------|------|----------|
| C7 无障碍违规量大，修复超出预估 | 中 | 40% | 延迟交付 1-2 天 | 先扫描后评估；若违规 >20 个/页面，优先修关键 (critical/serious) 项，moderate/minor 入后续 backlog |
| C8 安全测试依赖外部服务 (SMTP/Mailhog) | 低 | 20% | 测试环境搭建耗时 | 优先使用 mock；仅 C8-6 需真实 SMTP，可复用批次 D C4 的 Mailhog 配置 |
| C5 Strict Mode 修复引入 useApi 行为变化 | 低 | 15% | 影响 12 页面功能 | 修复后运行全平台页面回归 (C7 扫描过程自动覆盖页面加载) |
| axe-core 扫描结果与 Lighthouse 不一致 | 低 | 10% | 验收标准争议 | 以 axe-core 规则为准 (具体规则可追溯)，Lighthouse 作为参考评分不阻塞交付 |
| C6 文档过时风险 | 低 | 10% | 新人照做过时模式 | 文档中注明版本号 (v2.2)，在改进 backlog 中标记文档保鲜到期日 (2026-09) |

## 8. 产品决策记录

1. **C5 自研修复而非引入 TanStack Query**: Strict Mode 双挂载问题是 React 18 常见模式问题，通过 `useEffect` cleanup + 重新 fetch 修复即可，无需引入重量级依赖。保持批次 D 的产品决策——`useApi` 作为轻量方案。

2. **C6 优先文档化而非开发复合组件**: `DataTableAsyncState` 复合组件的收益取决于实际使用频率。当前 12 页面中仅 4 个 DataTable 页面，文档先行、观察团队反馈后再决定是否抽取复合组件。

3. **C7 以 axe-core 规则为准**: 因不同工具 (axe-core / Lighthouse / WAVE) 对同一页面可能报告不同违规项。以 axe-core 为标准 (规则可追溯、可复现)，Lighthouse 作为补充评分参考。

4. **C8 安全测试独立目录**: 安全回归测试独立于功能测试（`backend/tests/security/`），与功能测试（`backend/tests/test_*.py`）物理隔离。便于 CI 中按安全套件独立运行、独立统计覆盖率。

5. **批次 E 为 V2.2 最后批次**: 批次 E 完成后不再追加新的 P1 安全改进项。V2.2 安全基线发布后，后续安全改进纳入常规 backlog (Epic Sx 或新建 Epic)。

## 9. 交付物清单

| # | 交付物 | 类型 | 负责人 |
|---|--------|------|--------|
| 1 | `useApi.ts` Strict Mode 修复 (C5) | 代码 | 前端开发 |
| 2 | `state/README.md` 或等效文档 (C6) | 文档 | 前端开发 |
| 3 | 12 页面 axe-core 扫描报告 (C7) | 测试报告 | 前端/QA |
| 4 | 无障碍违规修复 commit (C7) | 代码 | 前端开发 |
| 5 | 12 页面无障碍截图 (C7) | 截图留档 | 前端开发 |
| 6 | `backend/tests/security/` 目录 (C8) | 测试代码 | 后端开发 |
| 7 | CI 安全回归步骤配置 (C8) | CI 配置 | 后端开发/DevOps |

## 10. 完成定义 (DoD)

- [ ] C5: `useApi` 在 Strict Mode 下无永久 loading，开发模式验证通过
- [ ] C6: 两种模式文档化，含完整代码示例，团队成员 Review 通过
- [ ] C7: 12 页面 axe-core 扫描 0 violation (豁免项记录在案)，3 核心页面 Lighthouse >= 90
- [ ] C8: 安全回归测试套件 8/8 覆盖，`pytest backend/tests/security/ -v` 全部通过
- [ ] CI 接入：安全回归测试在 PR 时自动运行，失败阻塞合并
- [ ] 所有改动合并至 `feature/p1-batch-a-security` 分支 -> PR 至 `develop`
- [ ] 批次 E Leader 放行验证通过
