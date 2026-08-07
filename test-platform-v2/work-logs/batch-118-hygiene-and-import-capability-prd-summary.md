# Batch 118 — PRD Summary（追踪器卫生清理 + C109-1 生产收尾 + 需求导入能力 C102-3/4 + C117-1）

> **Product (🟦)** | Date: 2026-08-07 | Status: Review | **mode: full**
> 判定：本批含新能力（C102-3 模块树直建、C102-4 差异标注、C117-1 覆盖缺口前端展示）→ 完整批次六件工件。

## 1. 问题陈述

1. **追踪器漂移（核心痛点）**：多项条件实际已完成但 `C-CONDITIONS.md` 仍标记 Open，导致后续批次误读、重复规划。已核实证据：
   - C102-2：生产 `GET /knowledge/search/health` 实测 `vector_search_functional=true`（hybrid，31 源/19 嵌入），capture source#31 等正常；
   - C110-3：批量执行/回填平台 UI 已存在（`frontend/src/pages/apitest/components/TaskTab.tsx`），C111-2 已 170/170 全绿；
   - C103-6/C102-5：coverage_report 已落地并关闭 C116-3；
   - C103-5：样本采集已收口（34 生产 XHR + C116-1 平台采集 314 样本）。
2. **C109-1 生产收尾未闭环**：`PLATFORM_FRONTEND_URL=https://cameltv-test-platform1.vercel.app` 已配置、生产库实测无 tester/viewer 演示账号（3 用户/0 演示），但 SEED_DEMO_USERS=false 生效确认与邀请链接端到端复测缺失。
3. **需求导入两大能力缺口**：模块树直建仍强制 `evidence_job_id`（`backend/app/api/v1/requirement_modules.py:368`）；生产页面 vs 原型差异标注只有 diff 基建（requirement.py diff_json / knowledge compare_iterations），无面向业务侧的能力交付。
4. **C117-1 覆盖缺口报告不可见**：后端 coverage_report 已产出，但前端 AiResultModal 无覆盖矩阵/缺口展示，测试人员无法在 UI 查看生成质量。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 追踪器卫生项关闭（C103-1~4/6、C102-2、C102-5、C110-3、C103-7 等） | 均 Open | 逐项证据核对后 Closed，`audit-cconditions.ps1` 0 硬错 | 本批合入时 |
| C109-1 闭环 | 未完成 | SEED_DEMO_USERS=false 生效确认 + 邀请链接复测 PASS | 本批合入+部署后 |
| C102-3 直建能力 | 不支持 | 需求文档直建模块树（不强制 evidence_job_id）+ 单测 | 本批 |
| C102-4 差异标注能力 | 不支持 | 生产页面 vs 原型差异标注可用 | 本批 |
| C117-1 前端展示 | 不可见 | AiResultModal 覆盖矩阵/缺口 Tab 可见 | 本批 |

## 3. 非目标（本次不做 + 豁免理由）

- **C117-2 异步多 worker**：依赖外部队列/Redis 基建，豁免转后续批次。
- **C106-2 邀请链接灰度观察一周**：时间窗口未到（2026-08-06 创建），保持 Open。
- **C96-1（C27-C1~C4 本地全栈验证）与 C99-1（PERF-OPT 性能优化）**：大项 Epic，本次豁免保持 Open。
- **外部 Deferred 项**（C101-2/3、C74-2/C95-1/C111-4、C111-1、CP-C2/C84-1、C95-2、C65-3、C63-2、C27-C1~4、batch-18-C7/C21-P1-5）：解除条件未满足（内网/凭据/设备），保持 Deferred 登记，本次不触碰。
- **C104-3/C105-3 api.d.ts 重生成**：本批仅核对漂移现状；若已收敛则关闭，否则转下批。
- **C105-4 停用组织 UI 走查**：若历史批次已有截图证据则核对关闭，否则转下批。
- **C113-1/C114-1/C114-2 交互拓扑核对**：核对 C115-4 连续 2 次 10/10 证据后关闭或转下批。

## 4. 用户故事 + 验收标准

- **US-1 追踪器卫生**：As a QA Lead, I want 追踪器与实际完成状态一致 so that 后续批次不再重复规划。
  验收：Given 已完成的条件 / When 逐项核对 production 实测 + evidence / Then 在 C-CONDITIONS.md Closed 表登记（带 PR/commit/证据路径），`audit-cconditions.ps1 -RequireLatestBatch` 0 硬错。
- **US-2 C109-1 生产收尾**：As a 测试工程师, I want 邀请链接生产链路闭环 so that 注册自动入项目/组织流程可信。
  验收：Given 生产配置 FRONTEND_URL 且 SEED_DEMO_USERS=false / When 浏览器打开邀请链接并完成注册 / Then https 页面 200、注册后自动入项目/组织、无 tester/viewer 演示账号重建。
- **US-3 C102-3 模块树直建**：As a 测试工程师, I want 从需求文档直接建模块树 so that 无蓝湖证据包也能梳理模块。
  验收：Given 需求文档（无 evidence_job_id）/ When 调用直建入口 / Then 模块树生成成功，单测覆盖直建与既有证据包两条路径。
- **US-4 C102-4 差异标注**：As a 测试工程师, I want 生产页面与需求原型差异标注 so that 英文站新模块（World Cup/Replays）迭代差异可视。
  验收：Given 生产页面数据 + 原型数据 / When 对比 / Then 差异（新增模块/变更页）标注返回并可展示。
- **US-5 C117-1 覆盖缺口前端展示**：As a 测试工程师, I want 生成结果里看到覆盖矩阵与缺口 so that 生成质量可评估。
  验收：Given AI 生成完成 / When 打开结果弹窗 / Then 覆盖矩阵/缺口 Tab 可见，数据来自 coverage_report 输出。

## 5. 技术考量

- C102-3：`requirement_modules.py` 新增无 evidence_job_id 的模块树直建端点（复用 `module_extractor.extract_module_tree`，输入切为需求文档文本/条目，而非证据包）；ModuleExtractRequest.evidence_job_id 改为可选，两条路径并存。
- C102-4：复用 knowledge `compare_iterations` / requirement `diff_json` 基建，新增「生产页面 vs 原型」差异标注端点；前端差异展示最小化（列表+标签）。
- C117-1：`AiResultModal` 增加覆盖矩阵/缺口 Tab，直接消费 `coverage_report.py` 的 JSON 输出结构。
- C109-1：SEED_DEMO_USERS 为 Railway 环境变量（backend config `seed_demo_users` 默认 True，`production.env` 未覆盖 → 需在 Railway 确认 false）；邀请链接复测用 Playwright 走注册流。
- 风险：生产 DB/环境只读优先；对 production.env 类本地运行时文件只读不提交。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main → Railway 自动部署 | 全平台 | C 追踪器 0 硬错；新能力单测+门禁全绿 |
| 部署后生产复测 | QA | C109-1 邀请链接复测 PASS；C102-2/capture 卫生证据复核 |

## 7. 技能使用

- `cameltv-agent-team`：六部门流水线（本工件所属）。
- `cameltv-bug-guard`：编码前避坑扫描（Dev）。
- `test-case-design`：涉及接口/功能用例核对时使用。
- `playwright-cli`/`playwright-skill`：C109-1 邀请链接端到端复测、C105-4 UI 走查证据（如需要）。
