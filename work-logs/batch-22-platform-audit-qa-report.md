# Batch 22 — 测试平台全面审查 QA 报告

> **QA (🔍)** | Date: 2026-07-19 | Verdict: **NEEDS WORK（22 项发现，6 项 P0）**

---

## 测试总览

| 指标 | 值 |
|------|-----|
| 审查维度 | 6（功能完整性 / 测试覆盖率 / 文档一致性 / 用户体验 / 性能 / 安全） |
| 发现总数 | 22 |
| P0 致命 | 6（文档脱节 5 项 + 核心能力缺失 1 项） |
| P1 严重 | 7 |
| P2 一般 | 7 |
| P3 建议 | 2 |
| 已验证证据 | ✅ 所有发现附文件:行号锚点（来自 3 个 Agent 代码探索 + 文档审查） |

---

## 逐维度验证

### 维度 1：功能完整性——「小白测试」愿景 vs 现实

| 检查项 | 预期 | 实际 | 判定 |
|--------|------|------|------|
| 提交需求 → AI 生成用例 | ✅ | `requirement_service.py` + `ai_service.py` 两段式生成 + 反向评审 | ✅ PASS |
| API 用例自动执行 | ✅ | `api_execution_service.py` httpx 真实执行 + 断言引擎 | ✅ PASS |
| UI 用例自动执行 | ✅ | `playwright_executor.py` 子进程管理，但需手工写 `.spec.ts` | ⚠️ 引擎就绪但缺编译器 |
| 功能用例自动执行 | ✅ | **不存在**——`case_type=manual` 无自动化通道 | ❌ P0 缺失 |
| 音视频检测真实执行 | ✅ | `av_check_service.py` + `ffmpeg_service.py` 真实探测 | ✅ PASS |
| 执行结果智能分诊 | ✅ | `failure_analyzer.py` 有基础模式匹配，未接 LLM | ⚠️ 基础存在但未达智能级别 |
| 执行结果 → 一键提缺陷 | ✅ | 不存在 | ❌ P1 缺失 |
| 审查队列持久化 | ✅ | `AiResultModal` 一次性弹窗 | ❌ P1 体验缺陷 |

### 维度 2：测试覆盖率

| 检查项 | 数据 | 判定 |
|--------|------|------|
| 后端测试函数数 | **612** 个（45 文件） | ✅ 数量充足 |
| 后端测试覆盖关键路径 | auth(12) + testcase(16) + testplan(8) + defect + knowledge(70) + wiki(42+) | ✅ 覆盖全面 |
| P1 安全回归 | `test_p1_security_regression.py`: 40 tests, 11 类 | ✅ |
| 前端 vitest | 仅 1 个 theme-provider test | ❌ P1 严重不足 |
| Playwright e2e | `smoke.spec.ts`: 1 个文件 13 页面可用性检查 | ⚠️ 仅冒烟，无功能验证 |
| CI 门禁 | 4 个 workflow（pr-check + develop-smoke + api-regression + prod-smoke） | ✅ |
| 测试契约漂移风险 | conftest 夹具已修复（StaticPool + auth_headers 对齐） | ✅ |

**关键缺口**：前端组件/页面单元测试为 0（`vitest` 存在但只测了 theme-provider）；Playwright e2e 只验证「页面不白屏」，不验证任何业务逻辑。

### 维度 3：文档一致性（本次审查最大发现）

> **2026-06-22 代码审查 PRD 的 6 条核心结论已全部过时，但文档从未更新。**

| 旧文档结论（2026-06-22） | 当前实际（2026-07-19） | 严重级 |
|--------------------------|------------------------|--------|
| "0 自动化测试" | 612 test functions + 5 CI workflows | **P0** |
| "缺 BaseService" | `core/base_service.py` 存在 | P1 |
| "真实 LLM API Key 明文硬编码" | `settings.validate_security()` 生产环境缺失即 fatal exit | P1 |
| "API 测试纯前端 fetch" | `api_execution_service.py` 934 行 httpx 真实执行 | **P0** |
| "UI 自动化随机数" | `playwright_executor.py` 517 行真实子进程管理 | **P0** |
| "音视频专项随机数" | `av_check_service.py` + `ffmpeg_service.py` 真实探测 | **P0** |
| frontend CLAUDE.md "apitest/uitest/special 演示态" | 三模块全接真实后端 | **P0** |
| onboarding.md curl 示例路径 `/api/v1/test-cases` | 实际 `/api/v1/testcase` | P2 |

### 维度 4：用户体验可用性

| 检查项 | 发现 | 判定 |
|--------|------|------|
| 登录页 | 无品牌标识 | P2 |
| 新用户引导 | 无 onboarding wizard，仅靠 docs | **P1** |
| 上传需求入口 | 藏在二级操作区 | P2 |
| AI 生成审查 | 一次性 Modal，关闭丢失 | **P1** |
| 执行操作 | 逐条手工，50 条 = 50 次点击 | **P1** |
| 错误提示 | Axios 拦截器已含 `detail` 字段（bug-guard F2 已修复） | ✅ |
| 加载/空/错误三态 | 仅 3 页面使用 AsyncState，15+ 页面手动管理 | P1 |

### 维度 5：性能

| 检查项 | 发现 | 判定 |
|--------|------|------|
| N+1 查询 | ✅ 已消除 | ✅ |
| 事务原子性 | ✅ 已修复 | ✅ |
| API 耗时追踪 | ❌ 无 request-id / 耗时日志 middleware | P1 |
| 前端 StrictMode 双重请求 | ✅ `useApi.ts` 有 `didInitialFetch` cleanup | ✅ |
| 前端捆绑包大小 | 未测量 | P3 |

### 维度 6：安全（P1 安全基线回归）

| 检查项 | 结果 |
|--------|------|
| JWT httpOnly Cookie (S1) | ✅ |
| XSS 防护 (S2) | ✅ |
| RBAC 权限补齐 (S3) | ✅ |
| 后台任务可靠性 (S4) | ✅ |
| SMTP TLS (S5) | ✅ |
| 文件上传安全 (S6) | ✅ |
| CSRF (S1d) | ✅ |
| Security Headers (C3) | ✅ |
| CSP (S2c) | ✅ |

**结论：8/8 项 P1 安全基线全部通过，无新增安全缺陷。**

---

## 缺陷清单

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| Q1 | **P0** | `CLAUDE.md` 模块表 API/UI/AV 成熟度标注落后实际 1-2 级 | Agent 代码探索确认三引擎真实执行，文档标注 🟡/🧪 | 待修复 |
| Q2 | **P0** | `现状功能PRD.md` 断言 API 测试「纯前端」、UI/AV「随机数」——全部过时 | Agent 代码探索确认 `api_execution_service.py:1-934` 等真实实现 | 待修复 |
| Q3 | **P0** | `frontend/CLAUDE.md` 标注三个演示态模块——实际全部真实 | `@/api/apitest`/`uitest`/`avcheck` 全部调用真实后端 | 待修复 |
| Q4 | **P0** | `代码审查PRD.md` 核心结论"0 测试/缺 BaseService/密钥硬编码"全部过时 | 612 tests + `core/base_service.py` + `validate_security()` | 待修复 |
| Q5 | **P0** | 功能用例（`case_type=manual`）无自动化执行通道 | `test_plan_service.py` 执行仅手工 `POST .../execute` | 待新功能 |
| Q6 | **P1** | 前端 0 业务组件/页面单元测试（vitest 仅测 theme-provider） | `frontend/src/components/__tests__/` 仅 1 文件 | 待补齐 |
| Q7 | **P1** | 15+ 页面的手动 loading/error 状态管理（AsyncState 未推广） | `defect/index.tsx:988` `report/index.tsx:644` 等 | 待标准化 |
| Q8 | **P1** | 无 request-id/耗时日志中间件 | 后端无全局请求追踪 | 待加 |
| Q9 | **P1** | Playwright e2e 仅冒烟，无业务逻辑验证 | `smoke.spec.ts` 只检查 body > 50 chars | 待加深 |
| Q10 | **P1** | AiResultModal 一次性弹窗——审查不可恢复 | `requirement/index.tsx` AiResultModal | 待改审查队列 |
| Q11 | **P1** | 无新用户 onboarding wizard | Design spec D9 | 待加 |
| Q12 | **P1** | 批量执行不统一——API/UI/AV 各有调度，无统一 TaskQueue 入口 | `api_task_worker.py` + `playwright_executor.py` + `ffmpeg_service.py` 各走各的 | 待统一 |
| Q13 | **P2** | `onboarding.md` curl 路径 `/api/v1/test-cases` 应为 `/api/v1/testcase` | `onboarding.md:38` | 待修正 |
| Q14 | **P2** | 双重主题系统并存（`data-theme` 遗留 4 套 + `data-theme-id` 产品 5 套） | `globals.css` 双系统 | 待合并 |
| Q15 | **P2** | `useChartColors` 主题切换不响应 | `use-chart-colors.ts:28` memo 只取一次 | 待修复 |
| Q16 | **P2** | 前端 `defect/index.tsx` 988 行超大组件 | `defect/index.tsx` | 待拆分 |
| Q17 | **P2** | Alembic 迁移 ID 风格不一致（时间戳 vs 描述名） | `versions/` 29 个文件 | 待统一 |
| Q18 | **P2** | AI 服务蓝湖路径硬编码 | `ai_service.py:14-16` | 待配置化 |
| Q19 | **P2** | AV 指标阈值硬编码 | `av_check_service.py:122` | 待落库 |
| Q20 | **P3** | 前端捆绑包大小未监控 | — | 待加 Lighthouse CI |
| Q21 | **P3** | knowledge 页面 9 个 Tab 全量 mount（无 `forceMount` 条件渲染验证） | `knowledge/index.tsx` | 待确认并修 |
| Q22 | **P3** | 文档保鲜仅月频运行 | `doc-freshness.yml` | 建议改为 per-batch 触发 |

---

## 发布建议

**状态: NEEDS WORK**

| 类别 | 数量 | 处理 |
|------|------|------|
| 必修复（P0） | 6 | 5 项文档同步即可修（Task 0b），1 项核心能力（功能用例自动执行） |
| 强烈建议（P1） | 7 | 前端测试 + AsyncState 迁移 + 中间件 + e2e + 审查队列 + 引导 + 编排统一 |
| 迭代优化（P2/P3） | 9 | 按 PM plan Slice 2/3 排入 |

**关键判断**：平台后端已**远超文档描述**——612 测试、安全基线全绿、三个专项引擎全部真实。问题是**文档拖了后腿**和**前端标准化未完成**。只要完成 Slice 0（文档同步）+ Slice 1（编译器和编排），小白愿景即可进入可演示状态。

---

**QA Agent**: 测试部门 🔍 | **日期**: 2026-07-19 | **下一步**: 移交 Leader
