# Batch 113 — PM Plan（知识中心模块-接口-功能关联基座 + UI 交互用例）

> **PM (🟨)** | Date: 2026-08-07

## 规格摘要

**原始需求**: PRD §1（C112-1 关联基座 + C112-2 交互用例）
**目标时间**: 1 开发日（切片 30–60 分钟）
**执行器**: codex（用户确认，batch-112 延续）

## 开发任务

### [ ] Task 1: 批次工件 + 看板 + 关联基座数据文件
**描述**: 写 PRD/PM/Design/看板；从功能模块地图 v2 §2/3/4/5 与 `evidence/batch-110/`
（nav.json、konfi-inventory-sports.json、xhr-samples-final.json、production-pages.json）
构建 `sports-module-interface-function-map.json`（module→function→interface→backend→konfi 关联）。
**验收标准**: 数据文件落盘；与地图/证据交叉核对无缺项；schema 字段齐全。
**涉及文件**: - `test-platform-v2/docs/体育平台-关联基座.json`（或 scripts 生成）
            - `scripts/sports/build-association-baseline.py`（新增）
**参考**: PRD §4 / 设计规范 §2

### [ ] Task 2: 知识中心入库 + 检索验证
**描述**: 将「功能模块地图 v2 + 关联基座」作为知识源导入知识中心（capture 通道，C110-2 已验证）；
验证 sources 可见 + RAG 检索命中（关键词：模块名/接口路径/formKey）。
**验收标准**: capture code 0 + source 可见；检索返回关联实体；证据 JSON 落盘。
**涉及文件**: - `scripts/sports/sync-association-knowledge.py`（新增）
            - `evidence/batch-113/knowledge-association-summary.json`
**参考**: PRD §4 / 设计规范 §3

### [ ] Task 3: 交互路径提取 + 交互用例生成/落库
**描述**: 从 production-pages.json（40 页路由）+ xhr-samples（page 字段）提取「页面→入口→目标页」
跳转清单；按 P0 模块（首页/赛事/直播/资讯/搜索/我的/联赛/回放/世界杯）生成交互用例
（正：入口可达/跳转/返回；负：直达无效 URL/空态/断链），落库功能用例库（交互域 + 正负向 + P0）。
**验收标准**: 路径清单 JSON + ≥15 条交互用例落库；与 UI 自动化映射衔接。
**涉及文件**: - `scripts/sports/generate-interaction-cases.py`（新增）
            - `evidence/batch-113/interaction-paths.json` + `interaction-cases-summary.json`
**参考**: PRD §4 / 设计规范 §4

### [ ] Task 4: QA 硬门禁 + QA/Leader + 一次总确认
**描述**: 执行脚本 py_compile、知识中心入库/检索验证、交互用例核对；写 QA/Leader；
展示变更摘要做一次总确认 → push → Draft PR。
**验收标准**: 工件齐全；audit-cconditions 0 硬错；用户总确认。

## 质量要求

- [ ] 关联数据与功能模块地图 v2 / evidence/batch-110 交叉核对（无编造接口/菜单）
- [ ] 知识中心入库走平台 API（capture），不以文档存在代替入库证据
- [ ] 交互用例遵循团队用例规范（正负向/步骤/预期/P0）
- [ ] 脚本 py_compile 0 错误；无调试残留；无硬编码密钥
- [ ] 生产数据只追加（知识源/用例），不删除既有资产
