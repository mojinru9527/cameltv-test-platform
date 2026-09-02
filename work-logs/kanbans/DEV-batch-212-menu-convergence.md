# 🗂️ Dev 部门项目看板 — Batch 212 入口收敛（B2 / menu-convergence）

## 📋 项目信息
| 字段 | 值 |
|------|-----|
| **项目名称** | 平台重构 B2：角色化菜单（tester 5 入口）+ C 级入口下架 + 旧测试计划入口删除 |
| **关联 PRD** | [batch-212-menu-convergence-prd-summary.md](../batch-212-menu-convergence-prd-summary.md) |
| **总预估工时** | 约 6h（实际约 6h） |
| **已用批次** | 1 批（完整：配置 + 前端） |
| **看板创建** | 2026-09-02 |
| **最后更新** | 2026-09-02 |

## 🎯 交付切片进度
| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 后端菜单配置：menu:testplan 下架（seed/HIDDEN/角色清单/目录测试） | ✅ | ✅ | ✅ | ✅ | ⏳ | pytest 17 绿 |
| 2 | 前端导航模型：顶层 5 行 + 资产与更多分桶（nav-config/MainNavRows/AssetsMoreGroup） | ✅ | ✅ | ✅ | ✅ | ⏳ | vitest 18 绿 |
| 3 | C 级入口下架：Playground Tab / knowledge 专家 Tab / 命令面板 / 访客目录 | ✅ | ✅ | ✅ | ✅ | ⏳ | vitest 全量 611 绿 |
| 4 | 旧 URL 处置 + 文档宣称下架：/testplan*、/playground 重定向；README；e2e 静态清单 | ✅ | ✅ | ✅ | ✅ | ⏳ | typecheck/build/lint 绿 |
| 5 | 路线图 §5 交接区 + C-CONDITIONS + 合规工件 | ✅ | ✅ | ✅ | ⏳ | ⏳ | QA 报告/Leader/看板 |
| 6 | QA：代码逻辑审计 + 小白走查（tester/admin 真实登录） | ✅ | ✅ | ✅ | ⏳ | ⏳ | 走查 14/14 绿 |

## 📍 当前位置
```
Batch 212（B2）— 开发与 QA 证据就绪
├── ✅ 后端 menu:testplan 下架（HIDDEN_MENU_CODES 拦截存量）+ 目录测试
├── ✅ 前端角色友好导航：tester 顶层 5 行 + 资产与更多分桶（资产/更多/专家/系统）
├── ✅ C 级下架：Playground Tab、知识专家 Tab、命令面板/访客目录/README special-perftest 宣称
├── ✅ /testplan* 与 /playground 重定向 /testcase（不 404）
├── ✅ 硬门禁：frontend typecheck/build/lint/vitest 611、backend ruff F821 + 受影响 pytest
├── ✅ 小白走查 14/14（tester/admin）证据 work-logs/evidence/batch-212/walkthrough/
└── ⏳ 待 Leader APPROVED → push → Draft PR → checks 绿 → squash 合入 main
```

## ⚠️ 阻塞与风险
| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| 无 | — | — | — | — |

## 🔗 相关工件
| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | work-logs/batch-212-menu-convergence-prd-summary.md | ✅ |
| PM 计划 | work-logs/batch-212-menu-convergence-pm-plan.md | ✅ |
| Design 规范 | work-logs/batch-212-menu-convergence-design-spec.md | ✅ |
| QA 报告 | work-logs/batch-212-menu-convergence-qa-report.md | ✅ |
| Leader 判决 | work-logs/batch-212-menu-convergence-leader-verdict.md | ✅ |
| 走查证据 | work-logs/evidence/batch-212/walkthrough/ | ✅ |
| C 条件 | C-CONDITIONS.md（batch-212 处理记录） | ✅ |