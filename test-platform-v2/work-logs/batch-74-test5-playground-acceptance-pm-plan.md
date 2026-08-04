# Batch 74 — PM Plan（Test5 契约登记 + Playground 实证 + J15/J16 验收）

> **PM (🟨)** | Date: 2026-08-04

## 开发任务

### [ ] Task 1: Test5 契约登记
**描述**: 新增可复现拉取脚本（WSL/OpenVPN 内网），从网关
`camel-api-gateway05.svc.elelive.cn`（解析 192.168.50.170）拉取全部路由服务 OpenAPI，
生成契约清单（服务/URL/版本/路径数/SHA-256/拉取时间）；更新
`docs/production-delivery/外部前置条件清单.md` 1.4 与 `待提供内容明细.md`。
**验收标准**: 脚本可重复执行；≥10 服务契约落盘；清单与事实一致（含网关路由表证据）。
**涉及文件**: `scripts/executor/fetch-test5-contracts.sh`、`test-platform-v2/tests/api-testing/specs/test5-contracts/`、
`docs/production-delivery/外部前置条件清单.md`、`docs/production-delivery/待提供内容明细.md`

### [ ] Task 2: Playground Gherkin→Playwright 映射改造
**描述**: `playground_service.py` 增加中文 Gherkin 动作映射（打开/访问/进入/点击/输入/填写/断言/看到/包含/等待/截图，
含「当/且/则」前缀），保留英文映射；`CompileRequest` 支持可选 `case_id`（存在则从功能用例步骤加载编译）；
补充单元测试覆盖中文步骤与无 TODO 断言。
**验收标准**: 中文用例步骤编译输出无 TODO、动作映射正确；`pytest test_playground.py` 全绿。
**涉及文件**: `backend/app/services/playground_service.py`、`backend/app/schemas/playground.py`、
`backend/app/api/v1/playground.py`、`backend/tests/test_playground.py`

### [ ] Task 3: Playground 实证（C22-C2/C3）与前端入口
**描述**: 后端（8041）+ 前端（5211）本地运行；先构造真实功能用例（TC-LIVE-001 等），
走 compile（含 case_id）→ tsc 校验 → headless Chromium 执行 → 截图；
再走统一编排 6/6（3 API + 3 功能）批量执行与报告生成；实证通过后新增 Playground 前端入口
（`/uitest` 或新 `/playground` 页）并同步菜单/命令面板/决策清单状态。
**验收标准**: C22-C2/C3 证据清单齐全（compile 全文/运行退出码/截图/执行记录/报告 xlsx）。
**涉及文件**: `frontend/src/pages/playground/`（新增）、`frontend/src/router/index.tsx`、
`docs/能力产品化决策清单.md`、`C-CONDITIONS.md`

### [ ] Task 4: J15 外部页只读验收
**描述**: 对 `https://www.camellofutbol.com` 只读 GET 页面执行真实浏览器自动化
（打开/断言关键内容/截图），证据写入批次 QA 报告；若链路走平台 uitest/playground，
则登记平台执行记录。
**验收标准**: 截图可见真实渲染 + 断言结果；仅只读，无登录/写入。
**涉及文件**: `test-platform-v2/work-logs/batch-74-*-qa-report.md`（证据附件）

### [ ] Task 5: J16 音视频 av-checks 验收
**描述**: 从 match replays 页面定位真实媒体地址（mp4/hls），用平台
`/av-checks`（ffprobe 探测）或等价 ffprobe 命令验证格式/帧率/音轨/健康，
结果（任务 id/指标/原始输出）登记。
**验收标准**: 真实媒体（非内置假文件）探测结果可复核；无伪造。
**涉及文件**: `test-platform-v2/work-logs/batch-74-*-qa-report.md`（证据附件）

### [ ] Task 6: QA + Leader + PR
**描述**: 六部门工件 + 看板；硬门禁（ruff F821、受影响 pytest/vitest、前端 typecheck/build）；
走 push 授权 → Draft PR → checks → 二次确认 → 合入。

## 质量要求
- [ ] ruff F821、受影响 pytest、前端 lint/typecheck/build、受影响 Vitest 全绿
- [ ] 每 PASS 带证据；外部项按 C63-2 登记（提供人/日期/授权范围），禁止伪造
