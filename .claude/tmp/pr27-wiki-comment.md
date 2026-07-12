## 🆕 增补：LLM-Wiki 结构化知识层与 RAG/Wiki 差异对比（batch-18/19/20）

本 PR 在原 M0-M6 知识线基础上，新增 **LLM-Wiki 能力（VNext-1..3）**，并已走完 Agent Team 六部门流水线放行。

### 功能（batch-18，提交 04c2b2e→f301ba0）
- VNext-1 蓝湖 Provider 化（抽取+委托，extract_features/generate_test_cases 零回归）+ Raw Source 去重/supersede
- VNext-2 平台内 Wiki 两阶段编译（LLM 分析→确定性生成，LLM 不可用降级；approved 不覆盖只 version+1）
- VNext-3 RAG vs Wiki 确定性差异分类器（7 类 diff_type + P0-P3）→ 转 pending AiArtifact 复用审核台
- 6 张 wiki_* 表 + 迁移 20260710_0017；所有能力默认开关 OFF（未开返回 HTTP 503）；RBAC 分权
- 前端知识中心新增「Wiki 知识库」「知识差异对比」两 Tab

### 六部门评审产物
work-logs/batch-18-wiki-diff-{prd-summary,pm-plan,design-spec,qa-report,leader-verdict}.md
Leader 裁决：APPROVED WITH CONDITIONS，亲验抽检 4/4 坐实。

### batch-19 合并前必办条件（提交 9200a7b，全清）
- C1 RBAC 越权修复：差异 accept/reject/create-artifact 权限 wiki:diff→wiki:approve + 审计
- C2 契约污染修复：_gather_wiki_text 仅纳入 approved 页 + 回归测试
- C3 新增 ADR-0013（GPLv3 借鉴 + 确定性分类器）

### batch-20 Design 两项 P1 收口（提交 2c7c1bb）
- P1-1 严重级四级可辨色梯度（新增 wikiSeverity.severityBadge，P0 红/P1 橙/P2 灰/P3 描边）
- P1-2 深色模式对比度：blue/emerald/amber 硬编码色全补 dark: 变体，满足 WCAG AA
- 设计签核升级为 Pass

### 验证
- 后端：wiki 专项 34 passed；全量 270 passed / 1 failed（test_ai_extraction_fallback 为改动前既存、与本线无关）
- 前端：tsc --noEmit + npm run build 通过

### 遗留（非合并阻断，排后续迭代/上线前）
P2/P3 设计项（状态中文映射、failed/running 分态+重试、evidence 结构化、触控目标、aria-label）；迁移 20260710_0017 staging 演练；review_items 持久化；差异召回率基线；灰度放量 SOP。
