# Playground 验收实证细则（C22-C2 / C22-C3）

> **用途**：明确 Playground（用例→Playwright 编译/执行）开放前端入口所需的两条实证（C22-C2/C3）的
> 精确步骤、验收口径与证据清单。实证通过后登记关闭 C72-2，并在「能力产品化决策清单」中将 Playground
> 从 API-only 转为正式 UI。

## 前置：compile 映射需真实化

当前 `POST /api/v1/playground/compile` 只把 Gherkin 源转成带 `// TODO: page.???` 的骨架（batch-72 实测）。
**实证前必须**先完成 Gherkin→Playwright 步骤映射（将「当/且/则」动作映射为 `page.goto / fill / click / expect`），
产出无 TODO 的可执行 .spec.ts。该代码改造应作为独立 Slice 先合入。

## C22-C2：第一条成功编译链路（P0 功能用例 → 可执行 spec → headless Chromium → 截图）

### 步骤
1. 在平台选择一条 P0 功能用例（建议 TC-LIVE-001「进入直播间默认播放视频流」）。
2. `POST /api/v1/playground/compile`（body：source=用例步骤、case_id=TC-LIVE-001）。
3. 校验返回 `spec_code`：
   - ✅ 无 `TODO` / `page.???` 占位；
   - ✅ 步骤按用例顺序映射为真实动作（goto 平台地址、等待元素、断言标题/元素）；
   - ✅ 可在本地运行（`npx playwright test <file>` 0 编译错误）。
4. headless Chromium 真实执行（对平台本地/测试环境页面）。
5. 收集产物：执行日志 + 截图（PNG）+ trace（可选）。

### 验收口径（P/N）
| 项 | P（通过） | N（失败） |
|---|-----------|-----------|
| 编译 | 无 TODO、动作映射正确、tsc 编译通过 | 有占位/TODO、语法错误 |
| 执行 | 用例步骤在真实页面完成（打开登录页/工作台）并断言 | 元素不存在/超时 → 明确失败，不接受 route mock 通过 |
| 产物 | 截图可见页面真实渲染 | 无截图或截图为空/报错 |
| 审计 | 执行记录写入平台（计划/执行模块） | 无记录或仅本地手工 |

### 证据清单
- compile 请求/响应（spec_code 全文）
- 运行命令与退出码（`npx playwright test` → 0）
- 截图文件（PNG）+ trace 文件路径
- 平台内执行记录（execution id / 状态）

## C22-C3：统一编排器一次完整批量执行（3 API + 3 功能 → 6/6 有结果 → 报告自动生成）

### 步骤
1. 准备 6 条用例：3 条 API（如登录/项目列表/用例列表，走真实后端）+ 3 条功能（如打开工作台/用例页/报告页）。
2. 统一编排器一次触发（平台「UI 自动化 / uitest」或批量执行入口，不得逐条手工串联）。
3. 等待全部完成：6/6 均有结果（pass/fail + 产物），任一失败需有明确错误与产物。
4. 自动生成报告（计划统计 → `POST /reports` → 导出 xlsx）。

### 验收口径
- 6/6 有结果，报告中统计与 DB 一致；
- 无 route mock / stub 通过；
- 报告可导出（xlsx）且内容含 6 条用例结果。

### 证据清单
- 编排器请求（6 条用例 id 列表）与逐条结果 JSON
- 报告 id + 导出文件（xlsx）
- 截图/trace 目录（每条功能用例 ≥1 张）

## 完成后
- 关闭 C22-C2、C22-C3、C72-2；
- 「能力产品化决策清单」Playground 行改为「正式 UI」；
- 在 `/uitest` 或新增前端入口接入 Playground。
