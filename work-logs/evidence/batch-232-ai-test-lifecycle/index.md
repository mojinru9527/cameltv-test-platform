# Batch 232 验收证据索引

> Date: 2026-09-07 | Environment: isolated local test platform + Test5 target | Mission: 9101 | Business verdict: FAIL

| 证据 ID | 覆盖范围 | 类型 | 基线/增量 | 对应文件 | 结论 | 复用规则 |
|---|---|---|---|---|---|---|
| E232-01 | 资料及 4 个需求片段 | 截图 | 增量 | `platform-ui/sources-desktop.png`, `platform-ui/source-fragments-desktop.png` | PASS | 资料模型未变时可复用 |
| E232-02 | 3 个范围项与冻结契约 | 截图 | 增量 | `platform-ui/scope-desktop.png`, `platform-ui/contract-desktop.png` | PASS | 范围/契约未变时可复用 |
| E232-03 | 功能/API/UI 场景与执行事实 | 截图 | 增量 | `platform-ui/scenarios-desktop.png`, `platform-ui/executions-desktop.png` | PARTIAL | 用例或 Run 变化后必须刷新 |
| E232-04 | Run #3 步骤、快照、截图/视频元数据 | 截图/回放 | 增量 | `platform-ui/replay-desktop.png` | FAIL | UI 复验后必须替换 |
| E232-05 | Build、Campaign、Quality Gate | 截图 | 增量 | `platform-ui/builds-desktop.png`, `platform-ui/acceptance-desktop.png` | FAIL (4/5) | Gate 重评后必须刷新 |
| E232-06 | 变化、影响、Lineage、缺口 | 截图 | 增量 | `platform-ui/changes-desktop.png`, `platform-ui/impact-desktop.png`, `platform-ui/lineage-desktop.png`, `platform-ui/gaps-desktop.png` | PASS/PARTIAL | 对应记录变化后刷新 |
| E232-07 | 概览三视口 | 截图 | 增量 | `platform-ui/overview-desktop.png`, `platform-ui/overview-tablet.png`, `platform-ui/overview-mobile.png` | PASS | 布局或生命周期模型变化后刷新 |
| E232-08 | 16 页/视口内容、网络、控制台 | 清单 | 增量 | `platform-ui/browser-report.json` | PASS | 页面/API 变化后重跑；不得只复用截图 |
| E232-09 | 功能用例录制 | PNG/WebM | 增量 | `retest-9101/functional-case.png`, `retest-9101/functional-case.webm` | PASS | 用例或 Test5 页面变化后刷新 |
| E232-10 | API 用例执行 | JSON/trace | 增量 | `retest-9101/api-case-result.json`, `retest-9101/api-case.trace` | PASS | 接口契约或环境变化后刷新 |
| E232-11 | UI 自动化录制 | PNG/WebM | 增量 | `retest-9101/ui-case.png`, `retest-9101/ui-case.webm` | FAIL | 缺陷修复后必须复验并新增父子 Run 证据 |
| E232-12 | Test5 初始语义快照与 Mission 复现数据 | 快照/脚本 | 增量 | `retest-9101/target-initial.yml`, `retest-9101/seed_mission_9101.py` | PASS | 仅用于本批隔离复现，生产数据不得由脚本伪造 |
| E232-13 | AI 缓存指标抽屉 | 截图/浏览器清单 | 增量 | `platform-ui/ai-cache-drawer-desktop.png`, `platform-ui/ai-cache-drawer-mobile.png`, `platform-ui/ai-cache-browser-report.json` | PASS | usage 展示或抽屉布局变化后刷新；无真实供应商 usage 时不得伪造数值 |

## 事实摘要

- 4 个非空需求片段、3 个已批准范围项、1 份冻结契约（3 条规则、3 个必需产出）。
- FUNCTIONAL/API/UI 各 1 条；3 次 Run、8 个步骤、8 个断言、6 个已验证物理证据、3 份回放清单。
- 1 个 Build、1 个 Campaign、1 个 Quality Gate；Gate 4/5，验收 FAIL。
- 3 个变更项、1 次影响分析（3 个受影响场景）、6 条 Lineage、1 个场景缺口。
- 浏览器报告：16 个检查、0 内容缺失、0 横向溢出、0 控制台错误、0 失败请求、0 重复有效 GET。
- AI 缓存抽屉：桌面与手机均无横向溢出、0 控制台错误、0 应用请求失败；历史空 usage 显示“—”，数值/0% 由自动化契约测试覆盖。

## 失败说明

Test5 UI 自动化观察到 11 个资源/控制台错误，包括 Google GSI 403、图片代理 503/504 和 NBA CDN HTTP2 错误。平台展示链路已经完整，但业务结论必须保持 FAIL，直到 `B232-TEST5-001` 修复并沿原 Run 复验。

## 边界

这些证据来自独立本地测试平台中的 Mission 9101，并以 `https://camel-bball-test5.elelive.cn/basketball` 为被测目标。它们不证明生产测试平台已经创建本任务，也不证明代码已经合入或发布生产。
