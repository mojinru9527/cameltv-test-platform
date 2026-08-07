# Batch 114 — PM Plan（交互拓扑 + UI 自动化 + 知识中心章节化）

> **PM (🟨)** | Date: 2026-08-07

## 规格摘要

**原始需求**: PRD §1（C113-1 拓扑+自动化 / C113-2 章节化）
**目标时间**: 1 开发日
**执行器**: codex（用户确认延续）

## 开发任务

### [ ] Task 1: 批次工件 + 看板 + 交互拓扑生成
**描述**: 写 PRD/PM/Design/看板；`build-interaction-topology.py` 消费
`evidence/batch-113/interaction-paths.json`（3172 边）→ 模块级拓扑（nodes/edges/入口聚合/P0）。
**验收标准**: `interaction-topology.json` + 文档落盘；P0 模块闭环（首页→赛事→直播间→回放等）。
**涉及文件**: - `scripts/sports/build-interaction-topology.py`（新增）
            - `test-platform-v2/docs/体育平台-交互拓扑.md` + `evidence/batch-114/interaction-topology.json`

### [ ] Task 2: 交互 UI 自动化 spec + 本地执行
**描述**: 新增 `backend/tests/playwright/specs/production-interaction.spec.ts`（复用只读守卫），
覆盖关键交互路径 ≥8 条（首页→赛事详情→直播间、首页→回放、资讯列表→详情、搜索→结果、我的渲染、返回恢复）；
本地执行全过 + 截图证据。
**验收标准**: 本地执行 全过；spec 挂平台 job 可运行。
**涉及文件**: - `backend/tests/playwright/specs/production-interaction.spec.ts`（新增）
            - `evidence/batch-114/ui-interaction-local/`

### [ ] Task 3: 平台 UI job 触发核对 + 知识中心章节化
**描述**: 平台 UI job 绑定交互 spec 触发运行核对；`sync-association-knowledge.py` 增强为按模块章节化
capture（每章节独立 source），模块词检索验证命中。
**验收标准**: 平台运行报告；章节化 source 可见 + 模块词检索命中对应章节。
**涉及文件**: - `scripts/sports/sync-association-knowledge.py`（增强）
            - `evidence/batch-114/knowledge-chaptered-summary.json`

### [ ] Task 4: QA 硬门禁 + QA/Leader + 一次总确认
**描述**: 执行本地/平台证据核对、py_compile、audit；写 QA/Leader；一次总确认 → push → PR。

## 质量要求

- [ ] 交互 spec 复用只读守卫（B112-4 口径），不引入写操作
- [ ] 章节化入库走平台 capture（非直连），检索为平台 RAG 实测
- [ ] 脚本 py_compile 0 错误；无调试残留
- [ ] 生产数据只追加，不删除既有 source/用例
