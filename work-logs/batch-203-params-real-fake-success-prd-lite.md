# Batch 203 — PRD-lite：参数真实化 + 假成功与状态一致性修复

> **Product (🟦)** | Date: 2026-08-24 | Status: 已合入 main（PR #313/#314）| Executor: DeepSeek_Harness | 轻量批次

```markdown
mode: light
豁免理由: 本批为黑盒 QA 报告（test-platform-v2/work-logs/blackbox-platform-modules-qa-report.md）已定位根因的「验收/修复」批次：无新行为、无新接口契约、无新配置项、无新依赖、无 schema/迁移变更，符合 pipeline-modes.md 轻量批次判定标准。
非目标: 不引入真实样本自动采集链路（generate_cases_from_real_sample 平台入口接入，仅保留既有 service 与 scripts/sports 逻辑）；不做缺陷状态机的数据库级约束/迁移（服务层校验）；不做通知 /notify/test 失败语义改造（B 组清单外）；不做生产网关/Test5 服务侧修复（外部依赖，登记 C203-2）。
```

## 1. 问题陈述

黑盒 QA 报告（2026-08-23 真实环境取证）确认平台「假数据/假成功」两条链路：

- **A 组·参数真实化**：OpenAPI 导入丢弃参数 `example/default/enum`（`openapi_import_service.py:320-325`）→ 生成器/调试面板产出占位假值（`test_xxx`/`ttt`/空值）→ 生成用例断言只查 2xx 无业务码 → 业务错误（网关 body `status=400`）被判「通过」；DebugTab URL 组装把 tags[0] 当模块路径、服务名双拼（证据：…/camel-service/sports-live-controller/ee/…）；preconditions 为硬编码空话；快速调试默认断言为空（「至少需要一个有效断言」必失败）。
- **B 组·假成功与状态一致性**：集成 sync-now 恒报「Sync complete」；调度触发硬编码 passed；Playground 含 TODO 判过；DSH 场景任务 0 产物标 success；缺陷 PUT 绕过六状态机；last_run_status/trace/report 词表不一致、缺 running/cancelled；DSH single 路径无心跳（300s 误回收闪烁）；发布包 parent_bundle_id 无表单入口；蓝湖任务无分页；删除被指派用户 500；认证零审计；会话缓存未按 X-Project-Id 隔离（跨项目泄漏）；UI 自动化默认「不绑定环境」且环境变量名与契约不一致。

## 2. 成功指标

| 指标 | 基线（QA 报告证据） | 目标 | 测量 |
|------|------|------|------|
| 复用证据 A 组 | URL=…/camel-service/sports-live-controller/ee/…；参数空值/占位；断言仅 2xx+rt；preconditions 空话；默认断言空 | URL=…/camel-test-confirm/ee/sports_live/home_match 与 …/live-platform/app/getByName；参数预填取契约真实值；生成断言=2xx+业务码+核心字段；preconditions 含认证/必填/接口说明；默认断言非空 | 本机 + VPN 真实对照组 |
| 引擎可信度 | getByName 200+真实 data（§8.2 C 组为目标值） | 修复后经平台执行同款请求仍 200 + 真实数据；不可达时诚实报错 | 对照组执行 |
| 假成功清零 | sync-now/调度/Playground/DSH/缺陷 PUT 恒成功 | 全部按真实结果/状态机返回，前端按 errors 提示 | 后端单测 + 前端 vitest |
| 硬门禁 | — | 后端 ruff F821、受影响全量 pytest 无新增失败；前端 vitest/typecheck/build 全绿 | 本批 QA 报告 |
| CI 门禁 | — | 双 PR required checks（双端全新检出全量回归 + AI/Git 交付策略）全绿 | GitHub Actions |

## 3. 修复范围（A/B 两分支，按交付顺序 A→B 合入）

| 域 | 覆盖点 |
|----|--------|
| A 组 | 导入保留 example/enum/default + `$ref`（参数/requestBody）解析；`_sample_value_for_prop`/`sampleValueForProp` 优先级；生成用例断言强制三项；DebugTab URL 统一 assetRoute；preconditions 契约描述；快速调试默认断言非空；release 门禁业务码路径识别 `$.status`/`$.resultCode` |
| B 组 | B1 sync-now 异常透出+前端 errors 提示 · B2 调度真实结果回填 · B3 Playground TODO 拦截 · B4 DSH 0 产物不 success · B5 缺陷 PUT 状态机（business envelope 200+code=1）· B6 last_run_status canonical 词表 · B7 trace/report 补 running/cancelled + 缺陷状态映射 · B8 DSH single 心跳 · B9 parent_bundle_id 表单 · B10 蓝湖分页 · B11 用户删除引用校验 · B12 认证审计（auth.*）· B13 缓存 key 纳入 X-Project-Id · B14 UI 自动化默认环境 + CAMELTV_BASE_URL 对齐 |

## 4. 交付物与合规

- 代码：PR #313（A 组，13 文件，main `fea9c602`）、PR #314（B 组，31 文件，main `98a26f4b`）
- 测试：`backend/tests/test_agroup_params_real.py`（17 例）、`test_unit_fake_success_state.py`（17 例）、前端 `utils.test.ts`/`assetRoute.test.ts`/`DebugTab.test.tsx` 扩展
- 本批合规工件：本 PRD-lite + QA 报告 + Leader Verdict（含流程回写/复盘卡）+ 看板 DEV-batch-203 + C203-1/C203-2 登记
