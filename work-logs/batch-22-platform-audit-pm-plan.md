# Batch 22 — 测试平台全面审查 PM Plan

> **PM (🟨)** | Date: 2026-07-19

## 规格摘要

**原始需求**: Product PRD — 填平「小白测试」愿景的最后一公里断裂：功能用例自动执行、API 用例一键执行、审查体验重构、文档体系事实核查

**技术栈**: FastAPI + SQLAlchemy 2.0（后端）/ React 18 + shadcn/ui + Vite 5（前端）

**目标时间**: 按切片独立交付，分 3 批次

---

## 🔍 Slice 0（P0 前置）：代码级事实核查 + 文档同步

> **必须先做**——连现状都不清楚就别谈改进。

### [ ] Task 0a: API/UI/AV 三个引擎代码级核查
**描述**: 逐文件核实 `apitest`/`uitest`/`special` 模块是否已从演示态升级为真实执行。检查 `api_execution_service.py` 是否真实 httpx 请求、`ui_test_service.py` 是否真实 Playwright 子进程、`av_check_service.py` 是否真实 ffprobe 探测。
**验收标准**:
- 输出事实核查报告：每个引擎的「真实执行代码行号」或「仍是 random/Math.random」的位置
- 与 `CLAUDE.md` 模块表 + `现状功能PRD.md` 对照，标注所有不一致处
**涉及文件**: `backend/app/services/api_execution_service.py` `backend/app/services/ui_test_service.py` `backend/app/services/av_check_service.py` `frontend/src/pages/apitest/` `frontend/src/pages/uitest/` `frontend/src/pages/special/`
**参考**: Product PRD §4/§5, `现状功能PRD.md` §模块11-13, backlog 批次五 V2.4

### [ ] Task 0b: 文档同步（CLAUDE.md + 现状 PRD + README）
**描述**: 根据 Task 0a 核查结果，更新所有文档中的模块成熟度标注，确保文档与代码一致。
**验收标准**:
- `CLAUDE.md` 模块表成熟度标注与代码实际状态一致
- `现状功能PRD.md` 中 API/UI/AV 三模块描述与代码一致，逐条附行号锚点
- README 技术栈描述（"Ant Design"→"shadcn/ui"）已修正
**涉及文件**: `test-platform-v2/CLAUDE.md` `test-platform-v2/docs/现状功能PRD.md` `test-platform-v2/README.md` `test-platform-v2/frontend/README.md`

---

## 🚀 Slice 1（P0 核心断裂）：功能用例自动执行通道

### [ ] Task 1a: 用例 → Playwright 脚本编译器
**描述**: 利用 LLM 将功能用例的 `steps` JSON（如 `[{"step":1,"action":"点击登录按钮","expected":"跳转到首页"}]`）编译为 Playwright `.spec.ts` 代码。关键词：零手工。
**验收标准**:
- API `POST /test-cases/{id}/compile` 返回可执行的 `.spec.ts` 内容
- 编译结果语法校验通过（`npx playwright test --dry-run`）
- 失败时有明确的错误行号和修复建议
- 支持 P0 用例优先编译
**涉及文件**: 新建 `backend/app/services/case_compiler_service.py`、`backend/app/api/v1/case_compiler.py`

### [ ] Task 1b: 批量执行编排引擎
**描述**: 从测试计划一键「全部执行」——逐条取用例的编译结果（或 API 用例的请求定义），用 TaskQueue 编排执行，每条执行结果自动回写计划。
**验收标准**:
- `POST /test-plans/{id}/auto-execute` 全量自动执行（当前端点存在但能力未知，需核查）
- 执行进度实时推送（SSE 或 polling）
- 支持并发度控制（默认 2 并发，避免打爆被测服务）
- 失败自动重试 1 次（区分「环境抖动」和「真失败」）
**涉及文件**: `backend/app/api/v1/test_plan.py` `backend/app/services/test_plan_service.py`

### [ ] Task 1c: API 用例一键执行
**描述**: AI 生成的 `api_cases[]` 导入用例库后，在用例详情页/计划执行时，自动将 `api_method/endpoint/headers/body` 转化为 httpx 请求并执行，零手工。引用环境变量 `${base_url}` 等。
**验收标准**:
- 用例详情页「执行」按钮对 API 类型用例自动走 httpx 引擎
- 环境变量引用解析正确（`${base_url}/api/users` → `http://test.example.com/api/users`）
- 断言引擎：支持 status_code / response_body contains / json_path / response_time < N ms
- 执行结果含 request/response 快照（方便审查）
**涉及文件**: `backend/app/services/api_execution_service.py` `frontend/src/pages/testcase/`

---

## 🎨 Slice 2（P0 审查体验）：小白审查工作流

### [ ] Task 2a: 审查队列（替代一次性弹窗）
**描述**: AI 生成用例后不再是一次性 `AiResultModal`，改为持久化的「审查队列」页面——可随时回来审查、支持分批复审。
**验收标准**:
- 新的 `/requirement/{id}/review` 页面：左侧 AI 生成的用例列表，右侧单条预览
- 支持 approve / reject / edit-before-import 三种操作
- 支持筛选：只看 P0 / 只看新增（与已导入对比）/ 只看接口用例
- 审查状态持久化，刷新不丢失
**涉及文件**: `frontend/src/pages/requirement/` 新建 `ReviewPage.tsx`、后端 `GET/PUT /requirement/{id}/review`

### [ ] Task 2b: 智能分诊——AI 预分析执行结果
**描述**: 批量执行完成后，调 LLM 分析失败用例，输出分类：真 bug / 环境抖动 / 用例缺陷 / 已知缺陷（关联已有 defect）。小白只看 AI 标红的。
**验收标准**:
- `POST /test-plans/{id}/triage` 返回每条失败用例的分类 + 置信度 + 解释
- 前端执行结果页按分类分组展示，真 bug 红色置顶
- 「一键提缺陷」：分类为「真 bug」的失败用例，一键创建缺陷（预填标题/步骤/实际结果）
**涉及文件**: 新建 `backend/app/services/triage_service.py`、前端执行结果页改造

### [ ] Task 2c: 需求输入简化
**描述**: 提供「一句话需求」输入框——"用户登录功能需要支持手机号+验证码方式"→ AI 展开为结构化需求文档 → 再生成用例。同时提供需求模板（功能需求/接口需求/回归需求）。
**验收标准**:
- 需求管理页新增「快速创建」按钮 → 一句话输入 + 模板选择
- AI 展开结果可编辑后再提交生成用例
- 蓝湖链接输入不再硬编码路径，改为可配置的 `LANHU_SKILLS_DIR`
**涉及文件**: `frontend/src/pages/requirement/` `backend/app/services/ai_service.py`

---

## 🧹 Slice 3（P1）：文档/UI 一致性 + 债务清理

### [ ] Task 3a: 文档保鲜机制
**描述**: 给每个 `last_reviewed` 字段过期的文档（> 30 天）+ CLAUDE.md 模块表建立保鲜检查脚本。
**验收标准**:
- `cameltv-doc-check` skill 可一键检查全部文档过期状态
- 本次审查完成后所有文档 `last_reviewed` 更新为 2026-07-19
**涉及文件**: `.claude/skills/cameltv-doc-check/SKILL.md` `test-platform-v2/docs/*.md`

### [ ] Task 3b: 前端 CRUD 重复代码抽取（usePaginatedList Hook）
**描述**: testcase/testplan/report/defect/schedule 等 6+ 页面复刻的分页+筛选+表格+删除模式，抽取为通用 Hook + CrudPage 壳组件。
**验收标准**:
- `usePaginatedList(fetchFn, options)` Hook：统一管理 loading/data/error/pagination/filters
- 至少 2 个页面完成迁移验证
**涉及文件**: 新建 `frontend/src/hooks/usePaginatedList.ts`、`frontend/src/components/CrudPage.tsx`

---

## 质量要求（全 Slice）

- [ ] 响应式设计通过（Desktop + Tablet）
- [ ] OpenAPI 文档同步更新
- [ ] 单元/集成测试覆盖核心路径
- [ ] 无障碍合规（ARIA labels, 键盘导航）
- [ ] 无 console 错误/告警
- [ ] 文档与代码锚点对齐（`文件:行号`）

## 依赖关系

```
Slice0(核查) → Slice1(执行通道) → Slice2(审查体验)
                                      ↘ Slice3(一致性+债务) 可并行
```

## 预估工时

| Slice | 任务数 | 后端工时 | 前端工时 | 合计 |
|-------|--------|---------|---------|------|
| 0 | 2 | 4h | 2h | 6h |
| 1 | 3 | 18h | 8h | 26h |
| 2 | 3 | 8h | 14h | 22h |
| 3 | 2 | 2h | 8h | 10h |
| **总计** | **10** | **32h** | **32h** | **64h** |

---

**PM Agent**: 项目管理部门 🟨 | **日期**: 2026-07-19 | **下一步**: 移交 Design / Dev 并行
