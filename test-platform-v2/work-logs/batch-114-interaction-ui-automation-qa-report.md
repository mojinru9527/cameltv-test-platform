# Batch 114 — QA 报告（交互拓扑 + UI 自动化 + 知识中心章节化）

> **QA (🔍)** | Date: 2026-08-07 | Verdict: 有条件通过（C113-1 平台 job 部署后核对）

## 1. 交付与证据

| 资产 | 结果 | 证据 |
|------|------|------|
| 交互拓扑（C113-1） | 3172 边 → **38 节点 / 119 边**（P0 9 节点 / 8 P0 边），首页→赛事→直播间→回放等闭环 | `evidence/batch-114/interaction-topology.json` + `docs/体育平台-交互拓扑.md` |
| 交互 UI 自动化（C113-1） | `production-interaction.spec.ts` **10 条关键交互路径本地 10/10 通过**（1.0m，含跳转/返回/Tab/搜索/回放/资讯/球队/世界杯） | `evidence/batch-114/ui-interaction-local/` 截图 + 运行日志 |
| 知识中心章节化（C113-2） | 关联基座按 13 用户模块拆章节 capture **全部 code=0（source id 18-30）**；模块词检索各 5 命中 | `evidence/batch-114/knowledge-chaptered-summary.json` |

## 2. 可执行门禁（命令 + 退出码）

| 门禁 | 结果 | 退出码 |
|------|------|--------|
| 脚本 py_compile（2 个） | ✅ 0 错误 | 0 |
| build-interaction-topology.py | ✅ 38 节点/119 边 + 文档 | 0 |
| 交互 spec 本地执行 | ✅ 10/10 passed（57-60s） | 0 |
| sync-association-knowledge.py（章节化） | ✅ 13 章节 capture code=0 + 检索 5×5 | 0 |
| scan-common-bugs（C76-2） | ✅ HARD=0 / WARN=209（基线持平） | 0（HARD） |
| 后端 pytest / 前端 typecheck | ⏸ 本批无后端/前端业务代码改动（仅 Playwright spec + 脚本 + 数据） | N/A |
| audit-cconditions | 🔄 Leader 阶段运行（0 硬错目标） | — |

## 3. 缺陷/障碍

| # | 级别 | 问题 | 证据 | 处理 |
|---|:----:|------|------|------|
| B114-1 | P3 | 首页首个 /match-replay 链接为隐藏导航项，初始断言误选 | 本地 run 复现 | spec 改用 :visible 定位（已修复，10/10） |

## 4. 诚实性说明

- 交互拓扑与 spec 全部基于生产页面真实链接/交互（batch-110 勘察 + 本地实跑），无杜撰。
- 平台 UI job 触发核对依赖交互 spec 合入部署（Railway 运行 main 代码），按 Batch 112 模式登记为
  部署后验证（C113-1 平台部分）；本地 10/10 已提供 spec 正确性证据。
- 章节化入库为平台标准 capture 实测（非直连），13 章节全部 code=0。

## 5. 发布建议

状态: **有条件通过**
必修复: 0 ｜ 条件: C113-1 平台交互 job 部署后触发核对（10/10）

## 6. 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1d / 实际 0.5d | 0/0/0/1 | 1 | 工具链 | 页面定位先确认可见性（:visible）再写断言 |

**技能使用**：`cameltv-agent-team`、`playwright-cli`/`playwright-skill`、`cameltv-bug-guard`。
