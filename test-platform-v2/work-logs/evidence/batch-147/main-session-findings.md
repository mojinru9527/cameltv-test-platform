# 主会话初步发现（供交叉核对，正式汇总在最终报告）

## 网络重复请求（Playwright CLI 27 页面遍历，network-main-session.jsonl）
- GET /api/v1/system/menus x28（登录后 1 + 27 页面各 1）→ C146-3 未修复，问题比 146（x15）更严重
- GET /api/v1/requirements x3（requirement/integration/knowledge?）
- GET /api/v1/test-cases x3（mindmap 全量 + testcase + integration 计数探针?）
- GET /api/v1/environments x3（apitest/uitest/integration）
- GET /api/v1/dashboard/stats x2（登录重定向 + workbench）
- GET /api/v1/lanhu-evidence/jobs x2
- GET /api/v1/release-bundles x2
- GET /api/v1/test-cases/domains x2

## 146 复测（主会话已确认）
- C146-1 P0 计划执行失败根因不可见：**仍存在**。计划 PLAN-AC9591BA 325 条全失败；执行历史「备注」仅显示「批量自动执行: POST /xx」，无 HTTP 状态/错误摘要；「链路」列全空。
- C146-5 计划页三执行按钮：**仍存在**（批量执行/标记完成/一键执行三按钮并存）。
- 146 UI-1 Command Palette 泄漏：**仍存在**（全页面 body 末尾出现 Command Palette/Search for a command to run...）。
- 用例 CRUD 闭环（API 直连）：创建(10187)→搜索→编辑→删除→404 验证，**全通**，临时数据已清理。
- 快速调试：发送按钮已存在（146「需先配断言才能发送」疑已修复），但 URL 拆 4 字段（服务器地址/服务名/模块名/接口路径）+ 完整请求地址并存；实际发请求未获响应（字段未填对，待 Agent 复核）。
- 工作台用例总数 7879（功能 7845/接口 34/自动化 0），通过率 0%——与 146 一致，统计口径问题（C146-2）仍存在。
- organization 页面显示「页面建设中」（非 404），与 146 UI-10 一致。

## 静态代码（主会话已确认）
- client.ts 无缓存/去重层（只有 401 跳登录 + toast 错误），confirm C146-3 根因。
- usePaginatedList.ts 0 引用（死代码）。
- 统计实现分散：dashboard.py/test_case.py/test_plan.py/report.py/trace.py/defect.py/interaction_coverage.py/knowledge.py/agent.py + services 层 10+ 文件。
