# Batch 211 — PRD-lite：平台重构基线方案落盘（B1）

> **Product (🟦)** | Date: 2026-09-02 | Status: Draft PR | Executor: Codex | 轻量批次

```markdown
mode: light
豁免理由: 本批为纯文档批次（docs/ + work-logs/）：定位方案、ABCD 去留白名单、术语映射、傻瓜化规范、B1–B15 落地路线图落盘。无代码、无新接口契约、无新配置项、无新依赖、无 schema/迁移变更，符合 pipeline-modes.md 轻量批次判定标准。
非目标: 不做任何入口/菜单改动（batch-212 做）；不删任何死代码（batch-215 做）；不建版本任务模型（batch-216 做）；不加埋点（owner 单用户，已取消）。
```

## 1. 背景与问题陈述

- 平台已建成「模块工具集合 + AITDE 引擎」双轨，22+ 顶级菜单/36+ 页面平铺，黑盒测试工程师上手难度极高；
- Owner 迷茫点：不知道平台定位、不知道哪些功能没用/重复/高复杂度低用、新业务如何接入；
- 用户定稿（2026-08/09 多轮决策）：
  1. 定位 = **AI 版本验收工作台**（面向黑盒测试工程师，主链路 = 版本验收任务）；
  2. 傻瓜化 = 让"傻子测试工程师"零培训可用（十诫 + 小白走查门禁）；
  3. ABCD 分级：A 做强主线 / B 收专家层 / C 砍入口+删死代码 / D 收敛重复；
  4. C 级具体：砍 Playground Tab、special/perftest 冻结为 API-only、知识中心普通视图只留 3 Tab、**旧测试计划独立入口直接删除**；**保留用例服务/接口/UI 为资产库**；全仓死代码全砍；
  5. 知识中心新增「AI 任务探索出来的新知识自动沉淀」双输入；
  6. 不做埋点（平台仅 owner 一人使用）；
  7. 执行 = 全部 Codex、每批新会话、每批代码实现逻辑审计 + 真实体育数据 mock 防假成功、推送/PR/合入一次授权、B1→B15 顺序直到完成、B15 后新会话终审 + 浏览器黑盒验收 + 交付文档。

## 2. 本批交付物

| 文件 | 说明 |
|------|------|
| docs/platform-refactor/README.md | 方案索引 |
| docs/platform-refactor/01-platform-positioning-and-mainline.md | 定位/双界面/主链路/知识闭环/新业务接入 |
| docs/platform-refactor/02-function-abc-whitelist.md | ABCD 分级去留白名单（用户定稿） |
| docs/platform-refactor/03-terminology-map.md | 引擎术语 → 业务 UI 词表 |
| docs/platform-refactor/04-foolproof-standards.md | 傻瓜化规范 + 小白走查门禁 |
| docs/superpowers/plans/2026-09-02-platform-refactor-rollout.md | B1–B15 路线图 + 批次映射 + 交接协议 |
| work-logs/batch-211-*-prd-lite/qa-report/leader-verdict + kanban | 本批合规工件 |

## 3. 成功指标

| 指标 | 目标 | 测量 |
|------|------|------|
| 方案完备 | 定位/白名单/术语/规范/路线图五类齐全且相互一致 | QA 交叉核对 |
| 可执行 | B1–B15 每批有内容/出口标准/交接协议 | 路线图核对 |
| 无代码改动 | 仅 docs/ + work-logs/ | git diff 核对 |
| 文档合规 | front-matter/链接/词表引用有效 | 本批 QA 报告 |

## 4. 下游依赖（供后续批引用）

- batch-212 入口收敛依赖 02 白名单 + 03 术语表；
- batch-215 死代码清理依赖 02 §3；
- batch-216 起主链路依赖 01 §4；
- 每批 PRD 必含「小白走查」节（04 §4）。