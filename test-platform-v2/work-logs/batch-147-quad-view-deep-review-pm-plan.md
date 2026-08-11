# Batch 147 — PM 计划（全平台四视角深度对抗审查·双 AI 交叉验证）

> **PM (🟨)** | Date: 2026-08-11 | 与 PRD 对齐，不加豪华需求

## 任务分解（30–60 min/任务）

| # | 任务 | 描述 | 验收标准 | 涉及文件/资源 |
|---|------|------|----------|----------------|
| T1 | 批次脚手架 | worktree/分支/PRD-lite/看板/PM/Design | 工件齐全，verify-ai-worktree 通过 | 本批工件 |
| T2 | 登录生产 + 全景盘点 | 登录生产，遍历全部路由/页面域，记录各页数据量与可操作性 | 全景清单（页面×数据量×入口） | 生产环境 + Network |
| T3 | 双 AI 分组独立走查 | Agent-A（UI+测试工程师）与 Agent-B（架构+甲方）并行深度走查全部模块 | 各分组发现 JSONL + 截图/快照证据 | evidence/batch-147/* |
| T4 | 交叉核对 + 146 复查 | 两 AI 发现清单交叉去重补漏；146 的 35 项发现逐条复测 | 交叉核对表 + 三态标注（已修/仍存在/新发现） | `pages.jsonl` + 报告 |
| T5 | 视角1 UI 报告 | 汇总 UI 发现（显示/操作/易用/一致/响应式/深色/空态/加载态） | `ui-report.md`，P0–P3 + 修复建议 + 证据 | 报告 |
| T6 | 视角2 测试工程师报告 | 功能/接口/UI 自动化三模块深度使用 + 体育适配/冗余/提效 + 四者关联优化 | `tester-report.md` | 报告 |
| T7 | 视角3 架构报告 | 架构问题 + 模块关联矩阵 + 空白机搭建（Win/mac）+ 重复请求清单 + C146-1~6 承接 | `architect-report.md` | 报告 |
| T8 | 视角4 甲方报告 | 功能流转梳理 + 差距 + 验收结论 | `client-report.md` | 报告 |
| T9 | xmind 生成 | 功能流转层 + 数据流转层（含问题标注、146→147 状态） | xmind 可打开、结构完整 | `docs/*147*.xmind` + JSON |
| T10 | 落地文档 | 问题-优先级-修复批次-状态 落地表，可直接驱动下版本修复 | `docs/batch-147-issue-landing.md` | 落地文档 |
| T11 | QA 报告 + 复盘卡 | 证据汇总、门禁记录、缺陷分级 | `qa-report.md` + 复盘卡 | 报告 |
| T12 | Leader 判决 + C 条件 | APPROVED/有条件通过、流程回写、C 条件同步 | `leader-verdict.md` + C-CONDITIONS 更新 | 报告 |
| T13 | 总确认 + PR + 合入 | 用户一次总确认 → push → Draft PR → checks → merge | PR 合入 main | GitHub |

## 依赖

- T2 依赖生产凭据（已提供 sportsadmin）
- T3 双 AI 并行（T2 完成后）
- T4 依赖 T3
- T5–T8 依赖 T4
- T9/T10 依赖 T5–T8
- T11/T12 依赖 T5–T10

## 资源

- 浏览器自动化：in-app browser（主会话）+ Playwright CLI（子智能体独立会话）
- 代码审查：worktree 内 `test-platform-v2/frontend/src` + `backend/app`
- 文档参考：`docs/测试平台使用手册.md`、`docs/现状功能PRD.md`、`docs/体育平台-功能模块地图.md`
- 技能：cameltv-agent-team（流水线）、cameltv-ui-conventions（UI 规范）、playwright-skill（浏览器）、cameltv-bug-guard（避坑）
