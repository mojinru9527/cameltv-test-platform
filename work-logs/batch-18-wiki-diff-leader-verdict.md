# Leader 终审裁决 — Batch 18 · LLM-Wiki 知识库差异对比能力（VNext-1..3）

- **签署人**：Team Leader（🎯 团队领导，终审门，独立于 Dev/QA，未参与编码）
- **裁决日期**：2026-07-10
- **被审交付**：VNext-1（蓝湖 Provider 化 + Raw Source）+ VNext-2（平台内 Wiki 两阶段编译）+ VNext-3（RAG vs Wiki 差异对比 + 转待审产物）；六部门流程回填评审
- **分支**：`feature/knowledge-m2-vector`（Wiki 5 提交 `04c2b2e`→`f301ba0`）→ 目标合并 `develop`
- **审查方式**：读四部门产物 + 逐行抽检真实源码（不信回执）+ 交叉验证各部门主张
- **最终裁决**：**APPROVED WITH CONDITIONS（有条件通过）** —— 基座质量达标、门禁默认安全、33 测试全绿；但抽检确认 QA 两项高优缺陷属实，须按放行条件收口后方可合入 develop。置信度 ~85%。

> 一句话：主链路（蓝湖→双库→差异→转产物）实现完整、纵切片划分清晰、契约不变性经我核验为**同一函数对象**、开关全 OFF（未开 503）使风险默认休眠——基座质量过关。但我亲验坐实了 QA 的两处真实缺陷：**差异处理三端点错挂 `wiki:diff` 致 Tester 越权**、**契约抽取只排 superseded 把已驳回/草稿 Wiki 页纳入对比**。二者均为低成本改动，定为【合并前必办】。故给**有条件通过**，非无条件放行，也非退回。

---

## 1. Review Summary

本批次是知识中心能力从"检索"迈向"结构化 + 可比对 + 可补齐"的关键一跃，落地 VNext-1..3 三条主链 + 基座，共 5 提交 / 5 切片 / 20 路由 / 6 表 / 8 后端 service / 5 前端组件 / 33 单测。DEV 部门按纵切片先行落地，Product / PM / Design / QA 四部门已完成流程回填评审。本次为 Agent Team 六部门流水线的**终审放行门**。

四部门汇报的收敛结论：
- **QA**：NEEDS WORK（信心 78%），2 项合入前必修（RBAC 越权 + 契约抽取污染）+ 5 项建议随迭代。
- **Design**：有条件通过，2 项 P1（严重级配色不可辨、深色模式对比度失效）。
- **Product**：主链路 DoD 达成，最实缺口是差异召回率/误报率无标注语料无法量化 + 灰度缺分环境 SOP。
- **PM**：交付率 5/5，遗留缺 ADR + 迁移未在 staging/生产演练。

我不照单全收，逐条抽检交叉验证如下（§3）。

---

## 2. 实现质量评级表

### 2.1 按切片

| 切片 | 交付 | 评级 | 风险 | 说明 |
|------|------|------|------|------|
| 切片 0 基座 | config 5 开关 + 6 表 + 迁移 0017 + seed 权限 + 路由/前端骨架 | ⭐⭐⭐⭐ | 🟡 | 结构完整；迁移仅 dev `AUTO_CREATE_TABLES` 验证，未 staging/生产演练 |
| VNext-1 Provider+RawSource | 蓝湖抽取 Provider 化 + Raw Source 去重/supersede | ⭐⭐⭐⭐⭐ | 🟢 | 契约不变性经我核验为同一函数对象（§3.4），回归兜底扎实 |
| VNext-2 Wiki 编译 | 两阶段 LLM 编译 + 页面版本化 + 审核门禁 | ⭐⭐⭐⭐ | 🟡 | approved 不覆盖、来源引用齐全；扣分：review_items/contradictions 未持久化（§13.3 未闭合） |
| VNext-3 差异对比+转产物 | 契约抽取 + 确定性 7 类分类 + 转 pending AiArtifact | ⭐⭐⭐ | 🔴 | 功能完整但含两处真实缺陷：RBAC 越权（§3.1）+ 契约抽取纳入已驳回页（§3.2） |
| 切片 4 前端收口 | 两 Tab 懒挂载 + 深链 + 发起对比入口 | ⭐⭐⭐⭐ | 🟡 | 视觉一致性好；扣分：Design 2 项 P1（配色/暗色对比度） |

### 2.2 按横向维度

| 维度 | 评级 | 风险 | 证据 |
|------|------|------|------|
| 测试完备度 | ⭐⭐⭐⭐ | 🟢 | 33/33 绿 + 回归 269 passed（唯一失败为预存在无关项）；扣分：`*_in_new_session` 编排层盲区 |
| 安全 / 门禁 | ⭐⭐⭐⭐ | 🟡 | 开关默认 OFF、未开真返 503；扣分：差异处理 RBAC 越权面偏大（§3.1） |
| 契约不变性 | ⭐⭐⭐⭐⭐ | 🟢 | `ai_service` 委托 `lanhu_provider` 同一函数对象（§3.4），既有蓝湖行为零回归 |
| 文档 / 架构治理 | ⭐⭐⭐ | 🟡 | 缺 ADR（新知识层 + GPLv3 借鉴属架构级）；差异召回率/误报率无基线 |

---

## 3. 抽检结果（逐处亲验，file:line 证据）

> 我亲自 Read/Grep 了 4 处关键代码，结论如下（✅确认 / ❌驳回各部门主张）。

### 3.1 ✅ 确认 QA① —— 差异处理三端点 RBAC 越权（安全，眼见为实）

**QA 主张成立。** 读 `app/api/v1/wiki.py`：
- `accept_diff_item`（`:390-402`）挂 `require_permission("wiki:diff")`（`:394`）
- `reject_diff_item`（`:405-417`）挂 `require_permission("wiki:diff")`（`:409`）
- `create_artifact`（`:420-442`）挂 `require_permission("wiki:diff")`（`:426`）

三端点全部用 `wiki:diff`（"发起对比"权限），而非"差异处理"应有的 `wiki:approve`。交叉核对 `seed.py`：`wiki:approve` 定义即为"审核 Wiki 页面**与差异处理**"（`:150`），证明方案本意差异处理归 approve；但 `_TESTER_ACTIONS` 默认授予 tester `wiki:view, wiki:diff`（`:160`）。**结论：默认持 `wiki:diff` 的 Tester 可采纳/忽略差异并一键生成 pending AiArtifact，绕过审核角色**——RBAC 越权属实。

**Leader 升级**：QA 定 P2，我按团队门槛"安全越权"**升为 P1** 并列【合并前必办】。附带发现（坐实 QA#6）：`accept`/`reject` 既无 `_require_wiki_diff_enabled()` 门禁、也无 `_audit`，而同链路 `create_artifact` 两者俱全（`:429` 有门禁、`:439` 有审计）——一并在 C1 收口。

### 3.2 ✅ 确认 QA② —— 契约抽取只排 superseded，纳入已驳回/草稿页

**QA 主张成立。** 读 `app/services/wiki/contract_extractor.py` `_gather_wiki_text`（`:41-53`）：筛选条件仅 `WikiPage.review_status != "superseded"`（`:46`）+ page_type 限定。**未排除 `rejected`/`draft`/`pending`**。结论：已被人工驳回或尚未审核的 Wiki 页仍作为"对比事实源"参与差异抽取，污染差异结果，并经 `create-artifact` 传导到待审产物。属实。定 P1，列【合并前必办】。

### 3.3 ✅ 确认 Design① —— 严重级 Badge P0/P1 同色

**Design 主张成立。** 读 `WikiDiffTab.tsx` `SEVERITY_VARIANT`（`:23-25`）：`P0: 'destructive', P1: 'destructive'`——最高两级同映射红色。差异对比的核心价值是按严重级分诊，最高两级视觉不可辨，削弱功能价值。`WikiDiffDetailDrawer.tsx` 同款映射。属实。因门禁默认 OFF、纯视觉问题，列【下批次跟进】。

### 3.4 ✅ 确认契约不变性 —— ai_service 委托 lanhu_provider（同一函数对象）

**DEV/QA 主张成立。** Grep `ai_service.py`：`:21` `from app.services.external.lanhu_provider import _extract_lanhu_content`，`:804`/`:903` 直接 `await _extract_lanhu_content(source_ref)`。委托的是 provider 里的**同一函数对象**（非拷贝重写），QA 的 `test_delegation_identity` 断言与此一致。结论：蓝湖抽取整体平移、`extract_features`/`generate_test_cases` 行为零回归，契约不变性成立。这是本批次风险最高的"字节级搬移"点，抽检通过给我放行信心。

**抽检小结：4/4 抽检项全部确认，无驳回。** QA 的两项高优缺陷坐实，Design P1 与契约不变性坐实。各部门无夸大或误报。

---

## 4. 跨部门发现收敛（去重归并总表）

| ID | 严重级 | 问题 | 来源 | 抽检 | 处置 |
|----|--------|------|------|------|------|
| F1 | **P1** | 差异 accept/reject/create-artifact 错挂 `wiki:diff`，Tester 越权采纳并生成待审产物（含 accept/reject 缺门禁+审计） | QA#1/#6 | ✅§3.1 | C1 合并前必办 |
| F2 | **P1** | 契约抽取 `_gather_wiki_text` 只排 superseded，纳入 rejected/draft 页污染差异 | QA#2 | ✅§3.2 | C2 合并前必办 |
| F3 | **P1** | 缺 ADR（新知识层架构 + GPLv3 借鉴属架构级决策） | PM | 与 batch-11 同类先例一致 | C3 合并前必办（轻量） |
| F4 | P1 | 严重级 Badge P0/P1 同为红色，最高两级不可辨 | Design P1-1 | ✅§3.3 | C4 下批次 |
| F5 | P1 | 硬编码浅色系无 `dark:` 变体，深色模式对比度低于 WCAG AA | Design P1-2 | 采信（多处 file:line 锚点） | C5 下批次 |
| F6 | P2 | review_items/contradictions 未持久化，无 WikiReviewItem 表，违反 §13.3 低置信进 Review | QA#3 | 采信 | C6 下批次 |
| F7 | P2 | 迁移 20260710_0017 未在 staging/生产演练 | PM/QA | 采信 | C7 上线前必办 |
| F8 | P2 | 差异召回率/误报率无标注语料无法量化 | Product | 采信（分类器确定性，质量依赖上游抽取） | C8 下批次 |
| F9 | P2 | 差异接口左右共用单 query，`compare_type`/`wiki_vs_wiki` 语义落空 | QA#4 | 采信 | C9 下批次/文档澄清 |
| F10 | P3 | `*_in_new_session` 编排层状态机/回滚无直接测试 | QA#5 | 采信 | C10 下批次 |
| F11 | P3 | import 未校验 `lanhu_mcp_enabled` 开关 | QA#7 | 采信 | C11 下批次 |
| F12 | P3 | 前端 WikiTab/WikiDiffTab 无组件测试、本次未跑 build/typecheck | QA#8 | 采信（仓库零组件单测约定） | C12 下批次 |
| F13 | P3 | 状态标签裸英文、失败态误用加载动画、JSON 裸展示、触控目标<44px、a11y label 缺失 | Design P2-3..P3-7 | 采信 | C13 下批次 |
| F14 | P3 | 灰度仅"开关 OFF"，缺分环境放量 SOP | Product/PM | 采信 | C14 下批次 |

---

## 5. 放行条件（Leader Conditions）

> 面向 batch-19（验收修复批次）。区分【合并 develop 前必办】与【可下批次跟进】。

### 5.1 【合并 develop 前必办】（3 项，均低成本）

**C1 — RBAC 权限修正（对应 F1 / QA#1+#6）**
- 动作：`api/v1/wiki.py` 将 `accept`/`reject`/`create-artifact` 三端点的 `require_permission("wiki:diff")` 收紧为 `require_permission("wiki:approve")`；并为 `accept`/`reject` 补 `_require_wiki_diff_enabled()` 门禁与 `_audit(...)`。
- 验收标准：默认持 `wiki:diff` 的 tester 调三端点返回 403；持 `wiki:approve` 者可通过；accept/reject 未开 `wiki_diff_enabled` 返回 503 且写审计日志；新增/更新对应权限回归用例并全绿。

**C2 — 契约抽取状态过滤（对应 F2 / QA#2）**
- 动作：`contract_extractor._gather_wiki_text` 过滤条件由"仅排 superseded"改为**仅纳入 `review_status == "approved"`（或至少排除 rejected/draft/pending/superseded）**。
- 验收标准：新增用例断言 rejected/draft 页不进入契约；差异结果不含已驳回页事实源。

**C3 — 补 ADR（对应 F3）**
- 动作：新增 `docs/adr/00XX-llm-wiki-knowledge-diff.md`，记录：自建 LLM-Wiki 层（Raw Source/Page/Link/Review/Diff）而非复制 GPLv3 源码的合规决策、确定性差异分类器 + LLM 仅辅助抽取的取舍、默认全 OFF 灰度、6 表 + 5 开关设计，关联 ADR-0002/0009。
- 验收标准：ADR 落盘、状态 Accepted、在 PR 引用。

> 依据：C1/C2 为安全与正确性缺陷且改动均为单点低成本，抽检坐实故不放行带病合入；C3 依 CLAUDE.md"架构级决策补 ADR"要求，与 batch-11 干净 GO 先例一致，轻量文档不阻塞进度。

### 5.2 【可下批次跟进 / 上线前硬门】（随 batch-19 或放开开关前收口）

| 条件 | 对应 | 验收标准 | 时点 |
|------|------|----------|------|
| C4 严重级配色四级可辨梯度（P1 独立橙色 + 暗色变体） | F4 | P0/P1/P2/P3 徽标视觉可辨，暗色下达 WCAG AA | batch-19 |
| C5 硬编码色补 `dark:` 变体或抽 info/success/warning 语义 Token | F5 | 深色模式对比度 ≥4.5:1，axe 无对比度告警 | batch-19 |
| C6 review_items/contradictions 持久化（新表或复用 AiArtifact） | F6 | 低置信/矛盾点可在审核台查看，§13.3 闭合 | 接入正式生成前 |
| **C7 迁移 20260710_0017 staging 演练** | F7 | staging `alembic upgrade head`/`downgrade` 双向验证通过并留痕 | **放开开关/生产上线前硬门** |
| C8 建标注语料评估差异召回率/误报率 | F8 | 给出召回率/误报率基线数值 | batch-19+ |
| C9 差异接口补 left/right 独立 ref/scope，或文档明确仅支持单 query+rag_vs_wiki | F9 | 接口能力与文档一致 | batch-19/文档 |
| C10 `*_in_new_session` 编排级测试（状态机+异常回滚） | F10 | running/success/failed/cancelled 守卫 + 回滚路径有断言 | batch-19 |
| C11 import 校验 `lanhu_mcp_enabled` | F11 | 关闭时导入被拒 | batch-19 |
| C12 前端 WikiTab/WikiDiffTab 测试 + 一次 build/typecheck 纳入 CI | F12 | 前端用例入 CI、typecheck 绿 | batch-19 |
| C13 状态中文映射 + 失败态拆分 + JSON 结构化 + 触控/a11y | F13 | 逐项达标 | batch-19 |
| C14 分环境灰度放量 SOP 文档 | F14 | "先 test 开 wiki_enabled→验证→再开 wiki_diff"成文 | batch-19 |

---

## 6. Verdict

### **APPROVED WITH CONDITIONS（有条件通过）** —— 置信度 ~85%

**理由**：VNext-1..3 主链路实现完整、纵切片清晰、33 单测全绿、回归无连带破坏、开关默认 OFF 使新链路风险合入不自动激活、契约不变性经我核验为同一函数对象——**基座质量达标**。但抽检坐实 QA 两项真实缺陷（RBAC 越权 + 契约抽取污染），均为代码级正确性/安全问题且改动低成本；叠加缺 ADR 的架构治理缺口。合理裁决为**有条件通过**：不退回（缺陷收敛、非结构性返工），也不无条件放行（存在已坐实的安全缺陷）。

**合入 develop 前置条件**：完成 §5.1 的 C1（RBAC 修正）、C2（契约状态过滤）、C3（补 ADR），并对 C1/C2 补齐回归用例、复跑 wiki 33 测试与回归子集全绿。三项收口后即转干净 GO，可合入。§5.2 各项随 batch-19 迭代或作为放开开关/上线前硬门（尤其 C7 迁移 staging 演练为生产上线前不可跳过）。

**代码现状**：已在 `feature/knowledge-m2-vector` 分支推送（`04c2b2e`→`f301ba0`），门禁 OFF 默认安全，合入前须先落 C1-C3。

---

## 7. 合并指令 + Post-Merge

### 合并指令（C1-C3 收口并复测通过后执行）

```bash
# 前置：C1/C2/C3 已提交，wiki 33 测试 + 回归子集全绿
git checkout develop
git pull origin develop
git merge feature/knowledge-m2-vector
git push origin develop
```

### Post-Merge 事项

- **放开开关前硬门**：`wiki_enabled`/`wiki_diff_enabled` 在任何环境置 ON 前，必须先完成 C7（迁移 staging 演练）与 C6（低置信进 Review 闭合）；生产放量遵循 C14 的分环境 SOP。
- **batch-19 领用**：Design C4/C5、测试 C10/C12、接口澄清 C9、召回率基线 C8、a11y C13 打包为 batch-19 验收修复清单。
- **CI 关注**：预存在失败 `test_ai_extraction_fallback` 与本批无关，但建议单独登记 backlog，避免长期红。
- 合入后按 [[agent-team-gate]] 归档六部门产物（本裁决书为流水线终审留痕）。

---

> 签署：Team Leader 🎯 ｜ 日期：2026-07-10 ｜ 复核对象：DEV 部门 VNext-1..3 + 四部门回填评审 ｜ 裁决：APPROVED WITH CONDITIONS（C1-C3 合并前必办）
