---
title: "AI 质量工程 Agent 落地方案：从需求到上线，开发直接按此写代码"
owner: "qa-team"
created: "2026-11-09"
last_reviewed: "2026-11-09"
status: "proposal"
tags: ["platform-refactor", "ai-agent", "landing-plan", "multi-end", "sports"]
related:
  - "docs/platform-refactor/09-platform-landing-plan.md"
  - "docs/platform-refactor/11-platform-simplification-design.md"
  - "work-logs/platform-simplification-production-eval-20261007.md"
  - "docs/standards/test-asset-map-standard.md"
  - "tests/test-case-standards/interaction-testing/interaction-methodology.md"
---

# AI 质量工程 Agent 落地方案

> 面向：平台开发团队（直接按此写代码）+ 项目负责人（先评审再开工）。
> 状态：`proposal`。未经 Agent Team 门禁。合入前走 `.claude/skills/cameltv-agent-team` 六部门流水线。
> 立场：**绝不重走 AITDE 老路**——不再自建"建模→编排→执行→愈合"闭环。
> 平台的角色是**编排层 + 证据脊柱 + 知识脊柱**；AI 的"脑"调用成熟开源 Agent，"腿"复用 `cameltv-node`。

---

## 0. 先修 P0，再谈 Agent（必须执行）

本方案任何"AI"能力落地前，以下 3 条 P0 必须先修完并真有证据，否则整份方案空转：

| ID | 阻塞项 | 定位 | 处置 | 验收 |
|----|-------|------|------|------|
| C274-1 | 生产 4 个 DeepSeek Key 实测全 401，ai-gateway 12 天零推理 | `work-logs/platform-simplification-production-eval-20261007.md` §3 | 轮换 Key → 入 `production.env` → `ai_config_service` 重连 → 真实发一次 `requirement→cases`，落 `ai_operation_records` 一条成功记录 | 新 record 时间戳 ≥ 当前；`openai`/`deepseek` 返回 200 的 curl 存证据包 |
| C274-2 | 简化批次将 DROP 104 张表（不可逆） | 同上 §5 | 执行前走一次完整备份恢复演练（batch-262 已证明链路可用）；表 DROP 迁移必带存在性守卫 | 备份→恢复→抽行一致；迁移干跑 dry-run 0 异常 |
| C273-5 | 生产磁盘 96% | 同上 §5 | 清理 + 扩盘；盘水位告警确认已送达 | 水位 ≤ 80% 维持 48 小时 |

> **门禁**：这 3 条都没做完就开始做"AI Agent"扩展，就是在把 AITDE 的失败模式复刻一遍。

---

## 1. 定位：平台做什么、不做什么

### 1.1 做什么（主线，与 11 号方案一致）

**一句话**：平台 = **"AI 版本验收工作台"** = 需求 → AI 生成计划 → 人审 → 执行调度 → 证据沉淀 → 缺陷 → 发布判定 → 版本知识 → 下一个版本复用。

主链路：

```text
需求文档
  │
  ▼
AI 生成「测试计划项 + 用例族」（LLM 直连，不走假 gateway）
  │                                     ← 注入：24 准则、缺陷模式库、历史 Oracle
  ▼
测试人员逐项审（4 按钮：采纳 / 修改 / 删除 / 追问）
  │
  ▼
ExecutionJob 调度（manual / api / web / mobile_web / miniapp / native / data）
  │
  ▼
cameltv-node 本地执行腿（装 Playwright / Midscene / Appium / curl / DB client）
  │                                     ← 调用：成熟开源 Agent（而非自写）
  ▼
Evidence Bundle（sha256 manifest + 截图 + 视频 + trace + HAR + console + DB 快照）
  │
  ▼
AI 分类失败（Product Bug / Automation Bug / System Issue / Known Noise）
  │
  ▼
缺陷草稿（带步骤 + 证据跳转 + 再跑按钮） / Oracle 校准 / 噪音规则沉淀
  │
  ▼
版本发布判定（PASS / CONDITIONAL / REJECT，绑证据包 sha256）
  │
  ▼
版本知识记录 + 影响图更新 + 复用建议注入下一个版本
```

### 1.2 不做什么（吸取 AITDE 教训）

明确不建 / 不碰：

- ❌ 不建第二套"Mission/Contract/Scenario/Oracle"建模层——24 准则 + Oracle 就是现成的建模。
- ❌ 不建第二套"Temporal/Workflow/Durable Runtime"——`task_queue.py` + ExecutionJob 已够用。
- ❌ 不建第二套"AI Gateway / Local Inference / Shadow Mode"——`ai_client` + `ai_config_service` 直连。
- ❌ 不写"planner stub + executor echo"——没有真实执行就不合并代码。
- ❌ 不在控制面跑浏览器/模型/ffmpeg（C263-1 要收口 `/uitest` 内置 browser）。
- ❌ 不用"用例数量增长"作为验收指标（04 禁令）。
- ❌ 不在 UI 文案里暴露"Oracle / Scenario / Contract"等引擎术语（03 术语图）。

---

## 2. 作为资深测试开发接手体育项目——一周例行节律

这节按真实工作节奏写，映射到平台触点（标 `→ 平台:` 为平台已/应提供）。读者可以直接把这当作一张"每日 checklist"。

### Day 1 — 读需求 / 读代码 / 读缺陷

**人做的事**：

1. 读蓝湖原型，列出"新增 / 改动 / 删除"的页面、交互和链路。
2. 问 PM：哪些字段上 ABtest？哪些是灰度？哪些带埋点？哪些涉及支付/风控？
3. 读代码 diff（上一版本 → 本版本），估算真实改动面（往往比 PRD 大）。
4. 读历史缺陷：本模块最近 3 个版本的漏测 Top 5 是什么形态？

**AI 做的事 / 平台触点**：

- `→ 平台:requirement` 蓝湖证据包 OCR → 结构化需求（已有，`lanhu_evidence`）。
- `→ 平台:ai`（本方案新增） **需求三源对账 Agent**：输入 PRD、蓝湖、代码 diff，输出"PRD 声明但代码未实现"、"代码实现但 PRD 未声明"、"蓝湖像素但文案/字段对不上"三张表。这是 §C-问题 1 的关键能力。
- `→ 平台:ai`（本方案新增） **缺陷画像 Agent**：按模块聚类历史缺陷，产出"本模块高频缺陷 TOP 3 形态 + 典型断言"，注入下一步生成用例的 prompt。

> **交付物**：`/version-tasks/new` 填好 title、version、changed modules、linked requirement 后，一键生成一份"需求-代码-原型对账单" + "历史缺陷模式摘要"，作为计划评审的输入。

### Day 2–3 — 拉契约 / 画页面地图 / 风险分级

**人做的事**：

1. 把本版本涉及到的接口拉一遍（Swagger / OpenAPI），确认 base_url、鉴权、数据流。
2. 画一张页面地图（admin 页 ↔ consumer 页 ↔ api）。
3. 给每条链路打一个 P0–P3 标签（根据影响面 + 频次 + 可观测性）。

**AI 做的事 / 平台触点**：

- `→ 平台:api` 自动拉 OpenAPI/Knife4j（已有，`openapi_import_service`）。
- `→ 平台:asset-map`（**合入**，见 §A5） 用 `scripts/test-asset-map/adapters.py` 合并"前端源码扫描 + mini-program app.json + PRD + 爬取"四源 → 页面清单。
- `→ 平台:ai`（本方案新增） **风险打分 Agent**：对每个页面/接口，结合"是否写库"、"是否涉及支付/VIP/身份"、"历史缺陷密度"、"本次改动行数"、"是否有埋点变更"输出 P0–P3 建议分。**AI 建议，人决策，不自动跑。**

### Day 4–5 — 生成测试计划 / 评审 / 修正

**人做的事**：评审 AI 生成的计划项，敲定 P0/P1 必跑清单。

**AI 做的事 / 平台触点**：

- `→ 平台:ai` `requirement→test_plan` 已跑过一次成功（703 条 / 99% 采纳率），本次改为**三阶段链式生成**（见 §B-技能库），而不是一次性梭哈：
  1. 阶段 1：**场景族（Scenario Family）**——穷举主要业务路径（正向 / 异常 / 边界 / 权限 / 并发 / 多端一致性）。
  2. 阶段 2：**断言绑定**——把 24 准则 + 项目 Oracle + 缺陷模式摘要注入，给每条场景绑可执行断言 ID（A01–A24）。
  3. 阶段 3：**覆盖率自检**——用 asset-map 的"断言覆盖率、接口分配率、链路可执行性"三指标打分，告诉人"还缺哪些"。

### Day 6–N — 执行 / 回归 / 发布判定

**人做的事**：盯执行流、确认失败是真 bug 还是噪音、改好后点回归、给发布判定。

**AI 做的事 / 平台触点**：

- `→ 平台:executions` **执行观察面**（**本方案新增**，见 §A1）——可以实时看到功能测试、接口测试、UI 自动化的 step 级进度 / 截图 / 请求响应，而不是只看一根进度条。
- `→ 平台:ai` **失败分类 Agent**（Playwright Healer + ReportPortal Auto-Analysis 的组合）——先判定失败簇（Product / Automation / Env / Flaky / Noise），再给出"本失败的最小复现步骤"。
- `→ 平台:defect` 从失败一键转缺陷，带 `linked_execution_id` + 证据跳转；缺陷修复后点"回归" → 重跑**同一** ExecutionJob（参数、环境、种子数据一致）→ 自动比对前后 trace 差异。

---

## 3. 技术路线：平台做编排，开源 Agent 做执行（组合，不自造）

### 3.1 分层

```text
┌──────────────────────────────────────────────────────────────────┐
│ Layer 4：平台 UI（React）                                          │
│   - 计划评审 / 执行观察面 / 证据回放 / 缺陷闭环 / 版本判定           │
├──────────────────────────────────────────────────────────────────┤
│ Layer 3：平台后端（FastAPI）                                       │
│   - 调度（ExecutionJob）/ 证据（EvidenceBundle）/ 知识（版本记录）  │
│   - AI 直连（ai_client + ai_config_service + ai_guard）            │
├──────────────────────────────────────────────────────────────────┤
│ Layer 2：Agent 技能库（Skill Pack，Agent Skills 开放标准）           │
│   - 规划（Planner）/ 执行（Executor）/ 校验（Oracle）/ 愈合（Healer）│
│   - 可被 Claude Code / Codex / Cursor / Copilot 共同加载             │
├──────────────────────────────────────────────────────────────────┤
│ Layer 1：执行腿（cameltv-node，装成熟开源 Agent 作为能力）           │
│   - Web：Playwright Test Agents (Planner/Generator/Healer)         │
│   - 跨端 UI：Midscene.js（iOS/Android/HarmonyOS/桌面/Web，视觉驱动）│
│   - 移动原生：Appium MCP Server（WDA / UIAutomator2）              │
│   - 复杂浏览：browser-use（表单/多站流）                            │
│   - 小程序：minium / weapp-dev-mcp                                  │
│   - 数据校验：直连 MySQL/Redis/MongoDB/Kafka（driver 内置）         │
│   - 失败分析：ReportPortal Auto-Analysis（ML 分类）                 │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 为什么不自写

| 自建 vs 复用 | 自建成本 | 复用方案 | 成熟度 |
|--------------|---------|---------|-------|
| Web Planner / Generator / Healer | AITDE 30 批次 0 Run | **Playwright Agents**（微软，2025-10）`npx playwright init-agents` | 官方维护，全球社区 |
| 跨端视觉 UI 自动化 | — | **Midscene.js**（字节 Web Infra），2026-04 支持 iOS/Android/HarmonyOS/桌面/Web | 开源活跃 |
| 原生移动 | 高 | **Appium MCP**（appium/appium-mcp） | 官方 |
| 复杂浏览（表单/多站） | 高 | **browser-use** 77k⭐ | 活跃 |
| 失败 ML 分类 | 高 | **ReportPortal**（Apache 2.0，内置 Auto-Analysis） | 老牌 |
| 用例生成 LLM 后端 | — | **DeepSeek / OpenAI** 直连 | 现有 |

> 来源：[Playwright Agents 官方](https://playwright.aims-ai.com/blog/playwright-whats-new-2026)、[Midscene.js](https://midscenejs.com/)、[Appium MCP](https://www.pulsemcp.com/servers/appium)、[browser-use](https://github.com/browser-use/browser-use)、[ReportPortal](https://reportportal.io/docs/features/AIFailureReasonDetection/)。

### 3.3 Agent Skills 开放标准（可移植性保障，见 §C-问题 5）

所有自己写的 Agent 能力统一封装为 **Agent Skills** 规范（Anthropic 2025-12-18 发布，Codex CLI / Cursor / Copilot 均已适配）：

```text
.claude/skills/<skill-name>/
  SKILL.md              # YAML frontmatter + 自然语言指令（progressive disclosure）
  references/           # 可选参考资料
  scripts/              # 可选可执行脚本
```

SKILL.md 遵循 progressive disclosure：name/description 全局常驻（短），正文仅在匹配时加载。这样同一个 skill 可以在：

- 本平台后端（`ai_service._load_skill_context_for()` 已跑通这个模式）
- 开发本机的 Claude Code / Codex
- 任意支持 Agent Skills 标准的 IDE

三处都生效，不改一行代码。

---

## 4. 架构：在现有代码上落 Agent 能力的 7 个接缝

本节是开发直接照着写代码的"接缝清单"。每条标注 **文件路径**、**改动类型**、**依赖**。

### 4.1 接缝 1：ExecutionJob 增加 Agent 任务类型

**文件**：`test-platform-v2/backend/app/services/execution_job_service.py`、`app/modules/campaign_execution/contracts.py`、`scripts/node/`。

**现状**：ExecutionJob 已有 `manual / api / web`；缺 `mobile_web / miniapp / native / data / interaction_chain`。

**改动**：

```python
# app/modules/campaign_execution/contracts.py
class ExecutionJobKind(str, Enum):
    MANUAL = "manual"              # 保留：人工执行
    API = "api"                    # 保留：接口用例
    WEB = "web"                    # 保留：Playwright Web UI
    # 新增：
    MOBILE_WEB = "mobile_web"      # 移动端浏览器（Playwright device emulation + 真实移动设备）
    MINIAPP = "miniapp"            # 小程序（minium / weapp-dev-mcp）
    NATIVE = "native"              # 原生 App（Appium MCP）
    INTERACTION_CHAIN = "interaction_chain"  # 跨端链路（admin→consumer 组合）
    DATA = "data"                  # 数据校验（SQL/Redis/MongoDB/Kafka）

class ExecutionJobProtocol(BaseModel):
    """节点与控制面之间的协议——一端扩展不影响另一端。"""
    job_id: str
    kind: ExecutionJobKind
    adapter_ref: str               # L2 适配器 key，决定 base_url / credential slot / page_source
    scenario_id: str               # 场景 ID（对应一组 case + assertion）
    env_snapshot_id: str           # 环境指纹（含版本号、构建号、种子数据版本）
    seed_data_ref: str | None      # 指向本次用的 fixture 快照（可空）
    assertion_ids: list[str]       # 需要校验的断言 ID（A01–A24 或项目扩展）
    expected_evidence_kinds: list[str]  # ["screenshot","video","trace","har","db_snapshot"]
    guardrails: GuardrailConfig    # H1-H5 的本任务级参数
```

**验收**：节点声明 `capabilities.available` 必须来自实测证据（延续现有 honesty 规则）；capabilities 文件示例：

```yaml
# scripts/node/capabilities.yaml（节点自描述）
node_id: "node-sports-win-01"
available:
  - id: web
    runner: playwright
    versions: { playwright: "1.56.0" }
    evidence: { last_pass_run_id: "exec_7731", last_pass_at: "2026-11-09T14:12:03+08:00" }
  - id: mobile_web
    runner: playwright
    devices: ["iPhone 14", "Pixel 7", "iPad Air"]
    evidence: { last_pass_run_id: "exec_7745" }
  - id: miniapp
    runner: weapp-dev-mcp
    # available: false 的能力这里不出现；出现即必须有 evidence 字段
```

### 4.2 接缝 2：AI 直连而非假 Gateway

**文件**：`app/services/ai_client.py`、`ai_config_service.py`、`ai_guard.py`。

**现状**：11 §6 D2 已经把 ai_job_dispatch / AiJob / AiResult 拆掉，`ai_gateway/` 残留需清理。`docs/ai/local-ai-agent.md` 文案过期。

**改动**：

1. 删除 `app/services/ai_gateway/`（随本方案批次一起）。
2. `ai_client` 直连 OpenAI 协议（DeepSeek、通义、Claude 等均可）；配置走 `ai_config_service`。
3. `ai_guard` 保留，承担：Token 额度 / Key 轮换探测 / 调用日志 / 熔断（连续 N 次 4xx 熔断并告警）。
4. 所有 AI 调用必写 `ai_operation_records` 一行（谁、哪个任务、prompt hash、latency、cost、status），**没写 record 的 AI 调用一律禁止**——这是 §C-问题 6 成长闭环的输入。
5. 更新 `docs/ai/local-ai-agent.md` 与 `scripts/ai_agent/README.md`，去掉"平台零推理"口径，写清楚新口径："平台只对需求→生成等文本类任务直连 LLM；浏览器/执行/证据全部在节点。"

### 4.3 接缝 3：Skill 注入管线扩容

**文件**：`app/services/ai_service.py::_load_skill_context_for()`、`.claude/skills/`。

**现状**：已经注入 `interaction-checklist.md`、`api-interaction-checklist.md`、`bug-pattern-digest.md`（29 patterns，16K 上限，有守卫测试 `test_interaction_skill_context.py`）。

**改动**：按**项目 Profile** 动态注入，而不是硬编码 futurewayu：

```python
# app/services/ai_service.py
def _load_skill_context_for(task_type: str, project_adapter: ProjectAdapter) -> str:
    base = [
        "tests/test-case-standards/interaction-testing/interaction-methodology.md",
        "tests/test-case-standards/interaction-testing/admin-and-consumer-interaction.md",
        "tests/test-case-standards/interaction-testing/platform-profiles.md",
        ".claude/skills/interaction-case-augmenter/references/interaction-checklist.md",
    ]
    # 项目 profile 决定哪些额外资料入 prompt
    profile = project_adapter.load_profile()  # L2 适配器里新字段：prompt_profile
    extra = [
        p.references  # e.g. ["sports-platform-glossary.md", "live-video-oracle.md"]
        for p in profile.applicable_profiles(task_type)
    ]
    extra.append(load_project_bug_pattern_digest(project_adapter.key, limit_bytes=8*1024))
    return concat_with_total_cap(base + extra, cap_bytes=24*1024)
```

**同步修复**（已知 L1 规则泄漏）：把 `.claude/skills/interaction-case-augmenter/SKILL.md §3` 里硬编码的 xinyuwadao/RuoYi/mini-program/Youzan 等项目名移到 `docs/standards/project-adapters/futurewayu.prompt-profile.yaml`。这是 §C-问题 4 跨项目的基础。

### 4.4 接缝 4：三阶段计划生成管线（替代一把梭）

**文件**（新增）：`app/services/plan_pipeline/`。

```text
app/services/plan_pipeline/
  __init__.py
  stage1_scenario_family.py    # 场景族穷举
  stage2_assertion_binding.py  # 24 准则 + 项目 Oracle + 缺陷模式注入
  stage3_coverage_self_check.py  # asset-map 三指标打分
  pipeline.py                  # 组合、重试、分块（大文档 B1 异步化顺带修）
```

每阶段单独一次 LLM 调用，各自落 `ai_operation_records`。**分块**：输入 >8K token 时按"章节 / 页"分块，每块产出后合并；大文档超时直接走异步任务队列，对接 `task_queue.py`，前端轮询 `/api/v1/plan-pipeline/:task_id`。这解决 SPORT-INT B1 / B5。

### 4.5 接缝 5：执行观察面（见 §A1）

见下一节。

### 4.6 接缝 6：证据回放组件统一化

**文件**：`frontend/src/components/evidence/`（新目录）。

**现状**（来自前端探测）：
- `pages/uitest/components/ProtectedArtifactMedia.tsx` 已有鉴权 blob 加载 + 图/视频渲染，但耦合 UI 测试 run。
- `components/execution/EvidenceBundlePanel.tsx` 已有完整度校验，但引用方 `LocalExecutionEvidenceSection.tsx` 没人用，等于死代码。
- `pages/apitest/components/TaskTab.tsx::SnapshotCard` 的请求/响应查看是全站最好的，但没 JSON tree / diff。
- 缺：Playwright trace zip 只能下载不能内嵌查看、HAR viewer、日志流、step timeline、JSON diff。

**改动**：抽成通用 `<EvidenceReplay evidenceBundleId=... />`，内含：

- `<StepTimeline />`：按时间轴展示 step 1→N，每步点开看 screenshot + request/response + console + trace 片段。
- `<ArtifactViewer kind="trace|har|video|screenshot|json|log" />`：按 kind 挑合适的 viewer（trace 用内嵌 Playwright trace viewer iframe、HAR 用 har-viewer、JSON 用 `<JsonTree />` + diff）。
- `<EvidenceCompleteness />`：复用 `EvidenceBundlePanel` 的完整度校验逻辑。

这是 §C-问题 7 执行观察的下半段。

### 4.7 接缝 7：缺陷 → 回归一键闭环

**文件**：`app/services/defect_service.py`、`frontend/src/pages/defect/`。

**现状**（来自前端探测）：
- 缺陷流有 `pending_review` 状态（待回归），但**没有"回归"按钮能触发执行**，只是一个状态标签。
- `DefectItem.execution_id` 字段存在但 UI 不展示。
- `description` 是 `<pre>` 自由文本，没有结构化"步骤 / 预期 / 实际 / 环境"字段。

**改动**：

1. 缺陷新增结构化字段（Alembic 迁移）：`steps_to_reproduce: JSON`、`expected: TEXT`、`actual: TEXT`、`env_snapshot_id: str`、`seed_data_ref: str`。失败一键转缺陷时，这些从 ExecutionJob + EvidenceBundle 自动回填。
2. 缺陷详情顶部新增：
   - 链路跳转：`#<linked_case>` ← → `#<execution_id>` ← → 证据包。
   - **"回归"按钮**（仅在 fixing / pending_review 状态可用）：`POST /api/v1/defects/:id/retest` → 用**原 job_id 的参数快照**重建 ExecutionJob（同 env_snapshot_id + seed_data_ref + assertion_ids），绑 `retest_of=original_execution_id`。
   - 回归结果页展示"前后 trace / 截图 / 关键断言"的 diff 视图。

```python
# app/services/defect_service.py 新增
async def retest(defect_id: str, actor: User) -> ExecutionJob:
    defect = await self.get(defect_id)
    if defect.status not in ("fixing", "pending_review"):
        raise InvalidState("retest only valid in fixing/pending_review")
    original = await self.get_execution(defect.execution_id)
    job = await self.exec_service.create(
        kind=original.kind,
        adapter_ref=original.adapter_ref,
        scenario_id=original.scenario_id,
        env_snapshot_id=original.env_snapshot_id,  # 关键：环境快照一致
        seed_data_ref=original.seed_data_ref,       # 关键：数据种子一致
        assertion_ids=original.assertion_ids,
        retest_of=original.execution_id,
        actor=actor,
    )
    await self.audit(defect_id, "retest_triggered", job_id=job.id, actor=actor)
    return job
```


---

## 5. 回答你的 11 个问题（每条都能对到上面的接缝）

### Q1. 需求评审和落地有偏差，怎么保证输出符合预期？

**问题本质**：PRD ≠ 代码 ≠ UI ≠ 测试理解，四者之间任何两个不一致都会漏测或过测。

**三源对账 + 三个 Oracle 层**：

1. **三源对账 Agent**（接缝 4 的 stage 0）：
   - 输入：PRD（含蓝湖）、代码 diff（git）、前端源码扫描（页面地图）。
   - 输出三张差异表：
     - **PRD 说了代码没做**：→ 回退 PM / 开发，不进入测试。
     - **代码做了 PRD 没说**：→ 可能是技术改造（可允许）或私改（必须拦）。
     - **蓝湖像素/文案 vs 代码不一致**：→ UI 回退设计。
   - 产出物作为**计划评审的强制输入**（不看对账单不能点"进入执行"）。

2. **三个 Oracle 层**（每条测试用例必须显式标明预期来自哪一层）：
   - **REQ**：PRD 原文直接引用（可追溯到章节行号）。
   - **STD**：行业或项目标准（24 准则、ISO 29119-4、WCAG 2.2）。
   - **PATTERN**：项目既往模式（缺陷模式库里的 test_oracle 字段）。
   - 任何用例没有 REQ/STD/PATTERN 之一绑定，CI 拒合（守卫规则 `scan-common-bugs.ps1` 扩一条）。

3. **可执行化**：
   - "页面正常/操作成功" 禁止作为预期（已在 interaction-methodology §3 定过）。
   - 预期必须拆到 UI 元素级（见 A01–A24），可被断言库捕获。

> **这才是"所见即所得"**：PRD 一句"后台上架 → C 端可见"，被拆成"后台 publish 调用返回 200 → 库 state=PUBLISHED → CDN 刷新 ≤5s → C 端列表接口返回 → 列表页出现 card → 点进详情页主图加载"，每步都有 A 编号断言绑着。

### Q2. 不同端（web / H5 / 小程序 / 原生 / 硬件）怎么在 Agent 里覆盖？

**问题本质**：各端运行时不同，不能一套脚本通吃；但测试意图（业务语义）必须一致。

**三层分工**：

| 层 | 做什么 | 文件 |
|----|--------|------|
| L1 L2 L3 共享断言意图 | 24 准则 + Oracle 层保持平台无关，描述业务语义 | `interaction-rules.json` |
| 适配器定义本端"怎么跑" | 每端一个 ExecutionJobKind + runner + capabilities | `scripts/node/capabilities.yaml` |
| 节点实际执行 | 挑对应 runner | `cameltv-node` |

**端对应**：

- **PC 浏览器**：Playwright + Playwright Agents（Planner/Generator/Healer）。
- **移动浏览器 / H5**：Playwright device emulation（375/414/768/1024）+ **真机 Playwright for Android**（Chromium Android）。
- **微信小程序**：先走 `weapp-dev-mcp` MCP server + `minium`；复杂交互退回"视觉+ADB"（Midscene.js Android 路径）。
- **iOS/Android 原生**：Appium MCP（WDA + UIAutomator2）；iOS 真机需先解掉 C84-1 的 WDA/usbmux 阻塞（三选一：Mac mini / Windows POC / API-only）。
- **桌面客户端**：Midscene.js 从 2026-04 支持 Windows/macOS/Linux。
- **硬件 / IoT**：按 `platform-profiles.md §5` 走"输入-状态-输出"模型；若设备无屏，断言打到网关 / MQTT / 后台读数据。

**跨端一致性**（admin 后台 ↔ C 端配合校验）：

新增 `ExecutionJobKind.INTERACTION_CHAIN`，由一个"主任务"编排多个子任务串行执行：

```yaml
# 示例：赛事上架 → C 端展示
kind: interaction_chain
chain_id: EVENT-PUBLISH-TO-CONSUMER
steps:
  - kind: web            # 后台
    adapter: cameltv-admin
    scenario: "创建赛事 & 发布"
    outputs: { event_id: "$.data.id" }           # 导出变量
  - kind: data           # 数据层校验
    adapter: cameltv-mysql-test
    assertion: |
      SELECT state FROM events WHERE id=${event_id}  --> 'PUBLISHED'
  - kind: api            # 接口层校验
    adapter: cameltv-api
    request: GET /live/list
    assertion: "$.data[?(@.id==${event_id})]"
  - kind: mobile_web     # C 端
    adapter: cameltv-h5
    scenario: "首页滚动找到 #${event_id} 卡片"
  - kind: miniapp        # 另一端
    adapter: cameltv-mp
    scenario: "首页滚动找到 #${event_id} 卡片"
```

**关键规则**：任何步骤失败，chain 立即停止并记录"失败在哪一跳"——admin / data / api / h5 / miniapp，这个"跳位"直接进缺陷归因（见 Q9 噪音识别的基础）。

### Q3. UI/交互怎么保证符合预期？

**问题本质**：UI 变化快、肉眼易漏、人检查不住。

**三件事**：

1. **24 条可执行准则**（已有，`run_assertions.py`）覆盖通用交互：溢出、对比度、焦点、响应式、重复触发、空态、异步任务、权限可见性等。每条准则有 A01–A24 的编号 + 可执行断言 + Playwright/HTTP 两种实现。

2. **视觉/像素 vs 蓝湖**：接入 Midscene.js 的 vision-based 匹配 + 蓝湖 MCP 的像素包做一次"关键页面像素差异扫描"。差异 > 阈值进二次人工复核（不自动拦，蓝湖切图本身偶尔跳变）。

3. **交互序列**（点击顺序 / 焦点漂移 / 返回键行为）用 Playwright trace 全程录制，trace viewer 嵌入证据回放。

**注意**：平台已有的 "`run_assertions.py web`" 已经能跑 R21 对比度、R22 响应式三档、R23 键盘焦点、R07 溢出。要做的是把它从 CLI 拉进平台：把断言结果写入 `EvidenceBundle.assertions`，前端在 `<StepTimeline />` 里按 A 编号着色显示。

### Q4. 非体育项目呢？会不会在 DB / Redis / MongoDB 层校验？

**问题本质**：不同项目后端栈不同，Oracle 可能在 UI / API / 数据库 / 缓存 / 消息队列 / 第三方回调 任何一处。

**答案是：会，而且必须。**

新增 `ExecutionJobKind.DATA`，统一走 `DataAssertion` 驱动：

```python
# app/services/data_assertion_service.py
class DataAssertion(BaseModel):
    kind: Literal["sql", "redis", "mongo", "kafka", "http_callback"]
    adapter_ref: str           # 指向 L2 adapter 里的连接 slot
    query: str                 # sql: SELECT; redis: GET/HGETALL; mongo: find; kafka: topic
    expected: Any              # 支持 jsonpath / regex / exact / range
    timeout_ms: int = 5000
    retry: RetryPolicy | None  # 对异步任务友好：每 500ms 重试，10s 内达到即 PASS
```

Driver 清单（都是现成库，不写新驱动）：

- SQL：SQLAlchemy / 项目原生 driver。
- Redis：`redis-py`。节点里已经有一条 `redis_cmd` 的历史坑（test-asset-map 里 `redis_get` 发成 GET 导致 KEYS 永远取不到），本次统一用 `redis.execute_command` 明确传命令字。
- MongoDB：`pymongo` / `motor`。
- Kafka：`aiokafka` consumer，带 group + offset 控制，避免抢消费。
- HTTP 回调：注册临时 webhook URL + 超时窗口。

**凭据**：数据层凭据永远只存节点的 `.env`（chmod 600），控制面不存（H3 原则）。

**项目举例**：

| 项目类型 | Oracle 可能在哪 |
|----------|-----------------|
| 体育直播（当前） | `events` 表 state、Redis `live:room:*`、CDN 刷新、API `/live/list` |
| 电商 | 订单表 status、库存表 stock、Redis 购物车、Kafka 支付回调、MongoDB 商品详情 |
| SaaS | 工单表、权限表（RBAC 层查用户-资源-动作关系）、审计流水 |
| IM | 会话表、Redis 在线状态、离线消息队列、ES 索引 |
| IoT | 设备影子（MQTT shadow）、时序库（InfluxDB）、规则引擎日志 |

每种只要在 L2 adapter 里登记 connection slot + query template，就能生成测试计划并执行。

### Q5. 能不能移植到 Codex / ChatGPT 上？

**可以，但有边界。**

- **技能层**（本方案 §3.3 Agent Skills）：100% 可移植。一个 SKILL.md 包同时被本平台 `ai_service._load_skill_context_for()`、Claude Code、Codex CLI、Cursor、Copilot 加载。Anthropic 2025-12-18 的 Agent Skills 开放标准官方宣称已被 OpenAI Codex CLI / Microsoft Agent Framework / Cursor / GitHub Copilot 适配。

- **执行层**（节点、浏览器、设备）：**不能移植**。Codex / ChatGPT 在你自己的云沙箱里跑，摸不到你公司内网、不能连 testdata5.elelive.cn、不能驱动真机。这是硬边界。

**现实方案（二合一）**：

1. 内网自建 **MCP Server** 包装平台能力：
   - `mcp://cameltv/exec` 暴露 ExecutionJob CRUD。
   - `mcp://cameltv/evidence` 暴露证据查询。
   - `mcp://cameltv/defects` 暴露缺陷读写。
   Codex / ChatGPT（企业版）通过 MCP 连到你的内网 MCP Server 就能驱动平台执行，自己不跑浏览器——"脑"在外、"腿"在内。

2. **AGENTS.md** 做入口说明（Codex 的标准配置文件已经有了，就是现在仓库根的 AGENTS.md），里面指明：
   - 要执行 QA 任务 → 读 `.claude/skills/<skill>` + 调 `mcp://cameltv/*`。
   - 禁止做的事（安全规则）。

> **坑**：Codex 的 sandbox 规则（不能摸 secret、不能 egress 到未授权域）要和平台的 H1-H5 对齐，不然对接会反复撞墙。

### Q6. 不同 Agent 之间有没有成长性？线上漏测 / 过程中发现的问题能不能学？

**三个反馈回路**，都基于已有数据：

1. **缺陷模式库成长**（`.claude/skills/bug-pattern-curator/`）：
   - 每条新修复缺陷 → PR merge 时 webhook → bug-pattern-curator skill 消费 → 产生/更新 pattern.yaml（含 `detection_point / trigger_signature / test_oracle`）。
   - 定期（周）跑覆盖率检查：现有用例族能否"触发 + 捕获"该 pattern？不行就标 `GAP`，加补充用例。
   - 现 29 条 pattern 的 futurewayu 版就是这么长出来的，复用这个机制。

2. **Oracle 自校准**（新增 `app/services/oracle_calibration.py`）：
   - 每次 ExecutionJob 完成，记录 `(assertion_id, pass/fail, false_positive_flag)`。
   - 同一断言在稳定环境下 10 次运行里 FP > 20% → 自动降级为 `NEEDS_REVIEW`，推给人复核。
   - 这是"flaky" 的平替——不叫 flaky 分析，就是 Oracle 质量标。

3. **Skill 迭代**：
   - Skill 文件走 git，每个 PR 带"修改理由 + 验证证据"（已有 test-case-design 的强制第 7 步）。
   - 平台 AI 调用的 skill context cap（24K）超限时按优先级裁剪：项目 profile > 24 准则 > bug pattern > 通用方法论，避免"塞越多越垃圾"。

> **反模式**：不要训 fine-tune 模型做"QA 领域专长"——数据量不够、维护负担大、没有必要。prompt + skill 已经够。

### Q7. 执行过程可见 + 一键回归

**执行观察面**（见 §4.5 / §A1），三类执行**三个标签页**但统一 UI：

| 执行类型 | 实时展示 | 步骤详情 | 证据 |
|----------|---------|---------|------|
| 功能（manual） | 进度 + 每步"开始/完成/标记失败" | 步骤文本 + 操作者输入的实际结果 + 手动截图 | 手动截图 / 手动日志 |
| 接口（api） | SSE 推 step events | request 全 + response 全 + assertion 结果 | request/response/assertion JSON |
| UI（web / mobile_web / miniapp / native） | SSE 推 step events + 实时缩略图 | 每 step 一个 screenshot 时间轴 | screenshot / video / trace / console / network |

**技术要点**：
- `GET /api/v1/executions/:id/events`（SSE）替代当前的手动 refresh。前端已有 `EvidenceTaskPanel` 的 polling 范式（3s backoff 3/6/12/30s，无重叠请求），升级为 SSE。
- 实时缩略图：节点每 2 秒推一张 1280×720 WebP（≤100KB）到 `/api/v1/executions/:id/live-frame`，前端 `<LiveFrame />` 显示最新的一张。

**一键回归**（见 §4.7）：
- 缺陷详情 → "回归"按钮 → 原参数 + 原 env_snapshot_id + 原 seed_data_ref 跑 → `retest_of` 绑定。
- 回归页：**diff 视图**——前后 trace / screenshot / console / API response 的三路对比。

### Q8. 不同端上同一个功能用例的执行过程怎么回看？

**跨端执行矩阵视图**（新增 `frontend/src/pages/executions/CrossEndMatrix.tsx`）：

```text
          │ Chrome-PC │ Safari-iOS │ 小程序-微信 │ Android-原生 │
──────────┼───────────┼────────────┼────────────┼──────────────┤
场景 S1   │   PASS ✓  │   FAIL ✗   │   PASS ✓   │    SKIP ⊘    │
场景 S2   │   PASS ✓  │   PASS ✓   │   FAIL ✗   │    PASS ✓    │
场景 S3   │   PASS ✓  │   PASS ✓   │   PASS ✓   │    PASS ✓    │
```

每格点击 → 跳到那次 ExecutionJob 的证据回放。
每行悬停 → 显示跨端一致性判定：
- **shared_behavior**：所有端期望一致，必须全 PASS。
- **platform_specific_behavior**：允许端差异（如 iOS 没有返回键手势），每端的预期分别写。
- **unsupported_behavior**：本端不支持此场景（标 SKIP，带理由）。
- **unknown_behavior**：未定义，报 BLOCK。

这是 `platform-profiles.md §6` 跨平台分类直接映射到 UI。

### Q9. 怎么规避测试噪音（广告只是例子）？

**问题拆分**：噪音 = 失败不是本次需求 bug，而是 ①其他需求影响 / ②环境问题 / ③数据脏 / ④第三方抖动 / ⑤脚本本身 flaky。

**四层识别（成本从低到高）**：

1. **基线差异**：
   - 本次 ExecutionJob 的 `env_snapshot_id` 对比基线 snapshot（版本号、构建 digest、种子数据版本）。
   - 不一致 → 失败前置原因标 `ENV_DRIFT`，不算 Product Bug。

2. **失败指纹（Fingerprint）**：
   - 每次失败生成指纹：`sha256(normalized_step + normalized_error + assertion_id)`。
   - 相同指纹**同时**出现在多个不相关场景 → 必是公共前置（环境 / 登录 / 数据），不是本场景 bug。
   - 这也是 ReportPortal Auto-Analysis 的核心思路，直接用它的 ML 服务做分类（Apache 2.0，开箱即用）。

3. **混杂因素识别 Agent**（新增）：
   - 输入：本次失败的 step events + 近 1 小时内同一环境的其他执行 events + 当前环境 active 的 feature flag 列表 + 当前环境部署的其他分支列表（CI/CD 元数据）。
   - LLM 分析输出 3 个可能的混杂因素及其置信度（广告 feature flag / 另一 PR 的数据库迁移 / 第三方登录接口抖动 / 自己脚本的等待不够）。
   - **不替代人判断**，只是在失败卡片上显示"疑似噪音：XXX（置信度 0.72）",人点"确认噪音"后进噪音规则库。

4. **噪音规则库**（持久化）：
   - 每条噪音规则：`{匹配条件: fingerprint OR step_regex OR error_regex, 归因: "feature_flag:ad_system / branch:feat-ad / 3rd_party:recaptcha"}`。
   - 下次匹配到相同模式 → 自动预标"已知噪音"但**仍跑**（避免真的 bug 被这个规则吃掉），需要人确认。
   - 规则库按项目 adapter 隔离，避免体育的广告规则污染电商项目。

**反模式**：不要"检测到广告就自动跳过广告"——这是你在例子里特意提醒的。广告也是业务，可能也有 bug。规避的是"这次失败不是本次需求 bug"的判断，不是"忽略广告"。

### Q10. GitHub 上有现成 Agent，直接拿来改不要造轮子

**完全同意，本方案就是这么设计的**。清单：

| 场景 | 复用项 | 接入方式 |
|------|--------|---------|
| Web UI 规划 / 生成 / 愈合 | **Playwright Agents** (Planner/Generator/Healer) | `cameltv-node` 内 `npx playwright init-agents`；platform 通过 ExecutionJob.kind=web 调度 |
| 跨端视觉自动化 | **Midscene.js**（ByteDance Web Infra，iOS/Android/HarmonyOS/桌面/Web） | 装为节点能力；通过视觉 locator 绕开"元素找不到"的 flaky |
| 原生移动 | **Appium MCP Server**（官方 / @gavrix / @Rahulec08 几个实现） | MCP server 跑在节点旁；Agent 通过 MCP 调用 |
| 复杂浏览流 | **browser-use**（77k⭐，Python） | 装为 node 能力；ExecutionJob.kind=web 的子策略之一 |
| TypeScript 栈的 AI 浏览器 | **Stagehand**（Browserbase，20k⭐） | 可选替代 |
| 表单-重的流 | **Skyvern**（YC，22k⭐） | 可选替代 |
| 失败 ML 分类 | **ReportPortal** 的 Auto-Analysis（Apache 2.0） | 独立部署 ReportPortal，节点把执行结果上报；拉 Auto-Analysis 结果进缺陷归因 |
| 小程序 | **minium** / **weapp-dev-mcp** | 节点能力 |
| LLM 后端 | DeepSeek / Qwen / Claude / GPT（OpenAI 协议） | `ai_client` 直连，已就绪 |

**原则**：节点装"真正有用"的开源组件，平台不在节点和开源组件之间插一层"抽象"。抽象层写得再好也抵不过一次 Playwright 升级跟不上的痛苦。

### Q11. 落地文档需要更详细，开发对着写即可

**本节下面的 §A1–§A7 就是——按 batch 拆到任务颗粒 + 文件路径 + API 契约 + 验收**。见下。

---

## 6. 具体落地方案（§A）：按 batch 拆，开发对照写即可

每个 batch 遵循 Agent Team 门禁：独立 worktree、分支命名 `feature/ai-agent-<batch>`、Draft PR、required checks 全绿、用户一次总确认、`audit-ai-pr.ps1` 通过。

### §A0（1-2 天，紧急）：P0 修复

| 任务 | 文件 | 验收 |
|------|------|------|
| A0-1 轮换生产 AI Key | `production.env`；`ai_config_service` 重连探测 | 一次真实 `requirement→cases` 落 `ai_operation_records` 并 200 |
| A0-2 备份演练 → 执行 11 号方案的 DROP | `test-platform-v2/backend/alembic/versions/` + 备份脚本 | 备份→恢复→抽行一致；DROP 迁移带存在性守卫 |
| A0-3 清理生产盘 + 盘水位告警 | `deploy/` / ops | 水位 ≤ 80%，告警送达记录 |

### §A1（1 周）：执行观察面

**分支**：`feature/ai-agent-a1-exec-observe`。

**文件**：
- 后端：`app/api/v1/executions.py`（新增 SSE endpoint）、`app/services/execution_live_stream.py`（新）、`app/services/evidence_bundle_service.py`（补字段）。
- 前端：`frontend/src/pages/executions/`（新目录）、`components/evidence/`（新，见接缝 6）。

**API**：

```text
GET  /api/v1/executions/:id                 # 详情（已有，补 steps/live_frame_url）
GET  /api/v1/executions/:id/events          # SSE：step_started / step_finished / assertion_result / live_frame
POST /api/v1/executions/:id/cancel          # 已有
GET  /api/v1/executions/:id/live-frame      # 最新缩略图（节点推上来）
```

**SSE 事件格式**：

```json
{"event":"step_started","step_id":"s1","at":"2026-11-09T10:00:00Z","title":"打开登录页"}
{"event":"step_screenshot","step_id":"s1","at":"2026-11-09T10:00:01Z","artifact_id":"a_123"}
{"event":"step_finished","step_id":"s1","at":"2026-11-09T10:00:03Z","status":"pass","duration_ms":3012}
{"event":"assertion_result","assertion_id":"A21","status":"fail","actual":2.46,"expected":">=4.5"}
{"event":"live_frame","url":"/api/v1/executions/exec_7731/live-frame","at":"..."}
```

**前端页面**：
- `/executions/:id`：顶部实时 LiveFrame + 进度 + 当前 step；中部 StepTimeline；底部 EvidenceReplay（点 step 跳相应证据）。
- `/executions/:id/compare?against=:other_id`：回归 diff。

**验收（Acceptance）**：
- 节点真实跑一个 Playwright web 任务，前端能看到 ≥3 张实时缩略图、≥1 个 step pass、≥1 个 assertion 结果——全链路实证（延续 honesty 原则，不能 echo）。
- 版本任务 run 页能跳到 `/executions/:id`（当前只能看文字 `查看 {url}`）。

### §A2（2 周）：ExecutionJob 执行腿 × 开源 Agent 接入

**分支**：`feature/ai-agent-a2-executor-legs`。

**任务**：

| 任务 | 做什么 | 验收（真实证据） |
|------|-------|-----------------|
| A2-1 Playwright Agents 技能化 | `.claude/skills/exec-web-playwright/SKILL.md` 包装 planner/generator/healer；`cameltv-node` 支持 `npx playwright init-agents` | 对体育 H5 的一个实际场景（如直播列表打开），由 skill 产出 .spec.ts，跑过并出 trace |
| A2-2 ExecutionJobKind.MOBILE_WEB | `app/modules/campaign_execution/contracts.py` 新 kind；节点 device emulation 默认矩阵（iPhone 14 / Pixel 7 / iPad Air） | 同一场景跑 3 档 device，证据包里 3 份独立 trace |
| A2-3 ExecutionJobKind.DATA | `app/services/data_assertion_service.py`（sql/redis/mongo/kafka/http_callback 五类） | 对体育 test5 MySQL/Redis 跑一次 Oracle 校验，返回真实值；凭据只在节点 |
| A2-4 ExecutionJobKind.INTERACTION_CHAIN | chain runner + 变量导出/注入；step 失败则 chain 停 + 归因到"跳位" | 跑一条 EVENT-PUBLISH-TO-CONSUMER，经 admin→data→api→h5，中间 h5 断言 fail，归因正确 |
| A2-5 Appium MCP 节点能力（可选） | 节点容器装 Appium + WDA / UIAutomator2；MCP server 跑旁路 | 可暂走 Android 真机，iOS 保持 C84-1 的三选一决策 |
| A2-6 Midscene.js 节点能力（可选） | 节点容器装 Midscene.js，作为 web/mobile_web/native 的降级/备选 runner | 一个视觉找不到元素的场景，走 Midscene 跑通 |

### §A3（1 周）：Evidence 回放 + 缺陷→回归闭环

**分支**：`feature/ai-agent-a3-evidence-defect-loop`。

**任务**：

| 任务 | 文件 | 验收 |
|------|------|------|
| A3-1 EvidenceReplay 通用组件 | `components/evidence/*` | 替换 UI/API/版本任务三处的查看入口；trace 内嵌不下载 |
| A3-2 Defect 结构化字段 | Alembic 迁移：`defects` 加 `steps_to_reproduce/expected/actual/env_snapshot_id/seed_data_ref/linked_execution_id` | 失败转缺陷自动回填；详情渲染结构化字段 |
| A3-3 一键回归 | `POST /defects/:id/retest`；前端按钮 | 修复缺陷后点回归，复用原参数真的跑；retest run 显示 diff |
| A3-4 跨端执行矩阵 | `pages/executions/CrossEndMatrix.tsx` | 同一场景跑 3 端后，矩阵视图亮三格；跨端一致性判定出现 |

### §A4（1-2 周）：失败分类 + 噪音规则

**分支**：`feature/ai-agent-a4-triage-noise`。

**任务**：

| 任务 | 文件 | 验收 |
|------|------|------|
| A4-1 ReportPortal 接入 | `deploy/docker-compose.reportportal.yml`；节点执行上报；platform 拉结果 | 一周数据后 Auto-Analysis 能把失败分三类（Product/Automation/System） |
| A4-2 失败指纹服务 | `app/services/failure_fingerprint_service.py` | 10 次失败聚成 3 组；跨场景聚簇正确率 ≥70%（人工复核） |
| A4-3 混杂因素识别 Agent | `app/services/noise_hint_agent.py`（LLM 调用，带 ai_operation_records） | 对一个真实"广告抖动"失败，Agent 产出"疑似：feature_flag:ad_v2 置信度 0.78" |
| A4-4 噪音规则库 | `models/noise_rules.py` + `/api/v1/noise-rules/*` CRUD | 人确认噪音后入库；下次自动预标，仍跑 |

### §A5（1 周）：资产底图进平台

**分支**：`feature/ai-agent-a5-asset-map-integration`。

**现状**：asset-map 已在 CLI/CI 跑通（futurewayu 2016 cells、sports 96 cells），但未并入平台 UI。

**任务**：

| 任务 | 文件 | 验收 |
|------|------|------|
| A5-1 页面地图入版本任务 | `app/services/asset_map_integration.py` 调 `scripts/test-asset-map/build_asset_map.py` | 版本任务 step 2 评审时展示本次涉及的页面清单（crawl+source+PRD 三源合并） |
| A5-2 24 准则断言结果进证据包 | `EvidenceBundle.assertions[].rule_id` | UI 回放时按 A 编号着色；"本次漏测的 R 编号"进版本判定 |
| A5-3 覆盖率三指标进版本判定 | `/api/v1/version-tasks/:id/coverage` | 版本判定页显示：断言覆盖率、接口分配率、链路可执行性 |
| A5-4 适配器移出硬编码 | 新 `docs/standards/project-adapters/cameltv-sports.adapter.yaml`（完整版，当前只有 api 一个 platform） + `.capabilities.yaml` + `.prompt-profile.yaml` | 跑一次体育项目全量资产底图，无 futurewayu 关键词泄漏 |

### §A6（2 周）：Agent 成长闭环

**分支**：`feature/ai-agent-a6-growth-loop`。

**任务**：

| 任务 | 文件 | 验收 |
|------|------|------|
| A6-1 PR→bug-pattern webhook | `app/services/bug_pattern_sync_service.py`（接 GitHub webhook） | 一条真实缺陷修复 PR 合并 → bug pattern yaml 自动 PR 出来 → 守卫测试跑过 |
| A6-2 Oracle 校准服务 | `app/services/oracle_calibration.py` | 对已有断言 10 次运行后，FP > 20% 的被标 NEEDS_REVIEW |
| A6-3 Skill context cap 智能裁剪 | `ai_service._load_skill_context_for()` 增 token budget | 大 PRD 场景下，context 不超 24K，按优先级裁 |

### §A7（持续）：Agent 可移植

**分支**：按批次独立。

| 任务 | 做什么 | 验收 |
|------|--------|------|
| A7-1 内网 MCP Server | `scripts/mcp-server/`：exec / evidence / defects / knowledge 四类 tools | Codex CLI 在公司网内可以 `mcp add cameltv ...` 调通 |
| A7-2 AGENTS.md 规整 | 补齐 `AGENTS.md` 的 Codex 适配段 | 在 Codex 开新 session，能读到并按此行动 |
| A7-3 Skill 跨 agent 验证 | 任选 3 个 skill 在 Claude Code / Codex / Cursor 分别加载跑通 | 三处证据截图 |


---

## 7. 技能库清单（§B）：要新建的 Agent Skills

存位：`.claude/skills/<skill-name>/SKILL.md`。所有 skill 走 Agent Skills 开放标准，Claude Code / Codex / Cursor 都能用。

| Skill | 用途 | 输入 | 输出 | 新/复用 |
|-------|------|------|------|---------|
| **requirement-three-source-reconciler** | 需求/代码/原型三源对账 | PRD.md、git diff、蓝湖 pack | 三张差异表（JSON） | 新建 |
| **defect-pattern-miner** | 缺陷画像 | project key、时间窗 | 本模块 Top 3 缺陷形态 + 典型断言 | 新建 |
| **risk-grader** | 风险打分 P0–P3 | page 列表 + change hints | 分级建议 + 理由 | 新建 |
| **plan-stage1-scenario-family** | 场景族生成 | PRD + adapter | ScenarioFamily JSON | 新建（接缝 4） |
| **plan-stage2-assertion-binder** | 场景绑 24 准则 + 项目 Oracle | ScenarioFamily + 缺陷模式 + 项目 profile | 绑定后的 Scenario | 新建（接缝 4） |
| **plan-stage3-coverage-checker** | 覆盖率三指标自检 | 绑定后的 Scenario + asset map | 覆盖率打分 + GAP 清单 | 新建（接缝 4） |
| **noise-hint-agent** | 疑似噪音归因 | 失败 step events + env flags + 其他 run events | 疑似因素 + 置信度 | 新建（§A4-3） |
| **exec-web-playwright** | Web 执行腿 | Scenario + adapter | spec.ts + run | 包装 Playwright Agents |
| **exec-mobile-web-playwright** | H5 执行腿 | + device matrix | 多 device trace | 包装 Playwright device emulation |
| **exec-native-appium** | 原生执行腿 | + 设备 UDID | screenshots + ui tree | 包装 Appium MCP |
| **exec-miniapp-weapp** | 小程序执行腿 | + mini program appId | screenshots + logs | 包装 minium / weapp-dev-mcp |
| **exec-data-assertion** | 数据层校验 | DataAssertion 对象 | pass/fail + actual value | 新建（接缝 1） |
| **interaction-case-augmenter** | 24 准则 + 缺陷模式注入 | PRD / Scenario | 增强后的用例 | **已有**（仅去硬编码） |
| **bug-pattern-curator** | 缺陷模式沉淀 | 修复 PR + closed defect | pattern.yaml | **已有** |
| **test-case-design** | 用例设计方法 | 需求片段 | 用例 | **已有**（删 AITDE 兼容段） |

每个 SKILL.md 遵循 progressive disclosure + 守卫测试：

```markdown
---
name: noise-hint-agent
description: 疑似测试噪音归因。输入失败证据 + 当前环境的 active feature flag + 并发执行的其他 run，输出 1-3 个疑似混杂因素 + 置信度。不替代人判断，只做提示。
---

## When
失败归因阶段，在 failure-triage 之后、人复核之前调用。

## Inputs
- execution_events: SSE stream dump
- active_flags: list[FeatureFlag]
- concurrent_runs: list[RunSummary]

## Output schema
{ "hints": [{ "factor": "...", "confidence": 0.0-1.0, "evidence_refs": [...] }] }

## Rules
- 必须给出证据引用（事件 ID / flag ID / 并发 run ID）
- 置信度 < 0.5 不输出
- 严禁推断"是 bug" or "不是 bug"——只输出"疑似混杂因素"
```

---

## 8. 多项目适配器清单（§C）：如何让平台支持新项目

接入新项目的 30 分钟清单（延续资产底图标准 §P0 流程）：

```yaml
# docs/standards/project-adapters/<project>.adapter.yaml
project: <project-key>
display_name: "..."

platforms:
  - { key: pc_web,       label: "PC 浏览器" }
  - { key: mobile_web,   label: "移动浏览器/H5" }
  - { key: miniapp,      label: "微信小程序" }
  - { key: android,      label: "Android 原生" }
  - { key: ios,          label: "iOS 原生" }
  - { key: api,          label: "接口" }

# 页面源（四源交叉）
pages:
  source: file
  path: ./pages/<project>-pages.json
  default_platform: pc_web
  kind_keywords: { ... }

# 接口源
interfaces:
  source: openapi
  path: ./openapi/<project>.yaml
  default_domain: core
  domain_map:
    - { name: live,    prefixes: ["/live/*", "/event/*"] }
    - { name: user,    prefixes: ["/user/*", "/auth/*"] }
    - { name: payment, prefixes: ["/pay/*"] }

# 环境连接 slot（节点读 .env 注入，控制面不存）
environment_slots:
  mysql: { host_env: CAMELTV_TEST_DB_HOST, user_env: CAMELTV_TEST_DB_USER, ... }
  redis: { host_env: CAMELTV_TEST_REDIS_HOST, ... }
  mongo: null                    # 不用则填 null
  kafka: null
  api_base: { env: CAMELTV_TEST_API_BASE }

# 跨端链路闭包
business_closures:
  - id: EVENT-PUBLISH-TO-CONSUMER
    name: "赛事上架到 C 端可见"
    chain: [admin_create, admin_publish, data_state, api_list, mobile_web_show, miniapp_show]

# prompt profile（指向与项目相关的额外 context，L1 规则不在此）
prompt_profile_path: ./cameltv-sports.prompt-profile.yaml
capabilities_path:   ./cameltv-sports.capabilities.yaml
```

**已有示例**：`futurewayu.adapter.yaml`、`cameltv-sports.adapter.yaml`（当前 sports 只有 api 一个 platform，本方案 A5-4 要补全）。

---

## 9. 不做清单（吸取 AITDE 教训，明文记录）

以下事项**本方案明确不做**，拒绝任何 PR 引入：

1. ❌ 不建第二套 Mission / Contract / Scenario / Oracle 建模实体。已有 ScenarioFamily + Assertion ID 就是建模。
2. ❌ 不建 Temporal / 自研 Durable Runtime。失败任务重试走 `task_queue.py` 的 soft delete + retry policy。
3. ❌ 不写"planner 生成 stub + executor echo"的管线。节点没真正跑起来就不合代码。
4. ❌ 不加"AI Gateway"抽象层。`ai_client` 直连。
5. ❌ 不加"Local Inference Shadow Mode"。文本类任务云端 LLM 够用；本地推理成本收益比低。
6. ❌ 不建第二套用例体系（"AI 用例库" vs "手工用例库"）——同一张表，字段上标 `generated_by=ai` 即可。
7. ❌ 不用用例数量作为 KPI——这是 04 foolproof 的禁令。
8. ❌ 不做"fine-tune 内部 QA 模型"——prompt + skill 足够。
9. ❌ 不在控制面跑 Playwright / Midscene / ffmpeg（C263-1 要彻底收口）。
10. ❌ 不写"AI 自证"脚本（AI 自己生成 + 自己跑 + 自己判 PASS）。任何 AI 产出必经人审或独立断言。
11. ❌ 不在生产环境做任何写操作。读也走只读账号 + `assert_public_url()` + 支付红线。

---

## 10. 风险与回滚

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| Playwright Agents 版本升级 break | 中 | 高 | 节点容器锁版本；每月定更检查；skill 带 `tested_against: playwright@1.56` |
| Midscene.js 视觉 locator 不稳定 | 中 | 中 | 只作为 Playwright locator 失败时的 fallback，不作首选 |
| LLM 成本失控 | 中 | 高 | `ai_guard` 已有额度闸门；`ai_operation_records` 周报告警 |
| MCP Server 暴露内网能力过多 | 低 | 很高 | 只暴露读接口 + 写接口走 token；非必要能力不暴露 |
| Skill Context 塞得过多拖慢响应 | 中 | 中 | A6-3 智能裁剪 + token budget |
| iOS 真机硬件阻塞 | 高 | 中 | 先做 Android + Web mobile；iOS 走 Mac mini / Windows POC / API-only 三选一 |

每个 batch 在 Agent Team 门禁下独立 revert（已有机制）；表 DROP 迁移必须可 downgrade（§A0-2 门禁）。

---

## 11. 下一步

1. **本文档走 Agent Team 门禁评审**（`.claude/skills/cameltv-agent-team`），形成 PRD → Design → Dev plan → QA report → Leader verdict。
2. **先过 §A0（P0 修复）**，证据不足不进 §A1。
3. **§A1–§A3 为第一波交付**（执行观察面 + 执行腿 + 证据闭环），一个月窗口。
4. **§A4–§A6 为第二波**（分类 + 噪音 + 成长），一到两个月。
5. **§A7 持续开展**，对 Codex / ChatGPT 的可移植性验证常态化。

---

## 附录 A：与现有文档的关系

- 继承 `09-platform-landing-plan.md` 的"控制面 + 本地节点"大结构。
- 继承 `11-platform-simplification-design.md` 的"最终形态"（≤4 一级入口 + 专家区 + AI 只留需求→生成）。
- 吸收 `work-logs/platform-simplification-production-eval-20261007.md` §3.3 的三条根因（执行链不落地 / 上手成本 / 多 AI 并存）。
- 复用 `docs/standards/test-asset-map-standard.md` 的 L1/L2/L3 + 24 准则 + 三指标。
- 复用 `tests/test-case-standards/interaction-testing/` 的方法论 + 五维角色模型 + 平台 profile。
- 新增 §4 七个接缝，均不与现有已删除清单冲突。

## 附录 B：开源 Agent 版本锁与许可证

| 组件 | 版本锁 | 许可证 | 备注 |
|------|--------|--------|------|
| Playwright | `1.56.x` 固定 | Apache 2.0 | `init-agents` 从 1.56 起支持 |
| Midscene.js | 最近小版本 | MIT | 2026-04 开始支持 iOS/Android/HarmonyOS |
| Appium MCP | 官方 server 最近 release | Apache 2.0 | 几个实现 pick 一个长期维护的 |
| browser-use | 最近小版本 | MIT | Python |
| ReportPortal | 最近 stable | Apache 2.0 | 需独立部署 |
| DeepSeek / OpenAI | API | — | 直连，OpenAI 协议 |

---

> 这份方案是 proposal。进 Agent Team 评审后以 Leader verdict 为准。

