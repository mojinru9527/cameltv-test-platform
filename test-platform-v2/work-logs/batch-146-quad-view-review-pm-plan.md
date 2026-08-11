# Batch 146 — PM 计划（四视角深度对抗审查）

> **PM (🟨)** | Date: 2026-08-11 | 与 PRD 对齐，不加豪华需求

## 任务分解（30–60 min/任务）

| # | 任务 | 描述 | 验收标准 | 涉及文件/资源 |
|---|------|------|----------|----------------|
| T1 | 批次脚手架 | worktree/分支/PRD-lite/看板/PM/Design | 工件齐全，verify-ai-worktree 通过 | 本批工件 |
| T2 | 登录生产 + 全景盘点 | 登录生产，遍历 31 路由/24 页面域，记录各页数据量与可操作性 | 全景清单（页面×数据量×入口） | 生产环境 + Network |
| T3 | 视角1 UI 审查 | 24 页面域对抗性 UI 体验（显示/操作/易用/一致性/响应式/深色模式/空态/加载态） | 每域≥10 项核查 + 截图证据 + P0–P3 定级 | `ui-report.md` + evidence |
| T4 | 视角2 测试工程师审查 | 功能/接口/UI 自动化三模块深度使用，体育项目真实数据 | 适配/不适配/冗余清单 + 四者关联优化方案 | `tester-report.md` |
| T5 | 视角3 架构审查 | 模块关联矩阵、请求冗余清单（Network+代码）、空白机搭建流程（Win/mac） | 架构问题 + 优化建议 + 重复请求证据 | `architect-report.md` |
| T6 | 视角4 甲方验收 | 逐模块功能流转梳理 + 与预期差距 | 流转图 + 差距清单 | `client-report.md` |
| T7 | xmind 生成 | 功能流转层 + 数据流转层 | xmind 可打开、结构完整、含问题标注 | `docs/*.xmind` |
| T8 | QA 报告 + 复盘卡 | 证据汇总、门禁记录、缺陷分级 | QA 报告 + 复盘卡 | `qa-report.md` |
| T9 | Leader 判决 + C 条件 | APPROVED/有条件通过、流程回写、C 条件同步 | verdict + C-CONDITIONS 更新 | `leader-verdict.md` |
| T10 | 总确认 + PR + 合入 | 用户总确认 → push → Draft PR → checks → merge | PR 合入 main | GitHub |

## 依赖

- T2 依赖用户生产凭据（P0 阻塞）
- T3/T4/T6 依赖 T2
- T5 静态部分（前端 API 层代码、请求 hook、文档）可在 T2 前并行执行
- T7 依赖 T3–T6 结论

## 资源

- 浏览器自动化：`browser-use` 技能（主会话，隔离会话 + Network 捕获）
- 代码审查：worktree 内 `test-platform-v2/frontend/src` + `backend/app`
- 文档参考：`测试平台使用手册.md`、`现状功能PRD.md`、`体育平台-功能模块地图.md`
