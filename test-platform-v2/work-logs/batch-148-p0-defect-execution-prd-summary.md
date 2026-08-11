# Batch 148 — P0 缺陷契约 + 执行根因可见/环境预检（PRD Summary）

> **Product (🟦)** | Date: 2026-08-11 | Status: Approved | Mode: full

mode: full
理由: 引入新行为（执行环境/Token 预检拦截、执行历史失败阶段列）与新 DB 字段（test_execution.status_code/error_type/error_message，Alembic 迁移），按 SKILL.md 判定为完整批次。
非目标: 统计口径收敛（Batch 149）、请求缓存/防抖/mindmap 聚合（Batch 150）、功能用例入计划与失败自动转缺陷/报告/通知（Batch 151）、文档/图谱/空白机引导（Batch 152+）不在本批实现；本批不改统计服务、不改 dashboard、不动知识图谱。

## 0. 背景与来源

- 来源：`docs/batch-147-issue-landing.md`（Batch 147 四视角深度对抗审查 + 双 AI 交叉验证，2026-08-11），承接 **FIX-147-P0-01 / FIX-147-P0-02**，对应 C 条件 **C147-1 / C147-2**（并承接 C146-1）。
- 用户 2026-08-11 指示：按落地建议从 Batch 148 开始实施，148 处理完即创建 PR 合入 main，再拉最新主干开发后续批次；执行器 = Codex，已一次性授权 148→152 的推送/PR/合入（本批总确认记录于 QA 报告）。

## 1. 问题陈述

### P0-01 缺陷新建 422 + React 整页崩溃（缺陷主写路径不可用）
- 前端 `DefectFormDialog` 默认 `assignee_id=null`（处理人「未指定」合法）；后端 `schemas/defect.py` `DefectCreate.assignee_id: int = 0` 为非 Optional → Pydantic 422。
- FastAPI 422 响应 `detail` 为对象数组；前端 `client.ts` 错误提取链 `msg || detail || message` 直接把数组塞给 `toast.error` → React 渲染非字符串 child → 整页崩溃。
- 影响：新建缺陷主写路径不可用（生产复现 2026-08-11）。

### P0-02 一键执行 325/325 失败且根因不可见
- 计划执行未绑定环境 → `_resolve_url` 无环境时给相对路径加 `http://` 前缀 → 生成 `http:///path` 非法 URL → TARGET_POLICY 失败。
- `actual_result` JSON 中已含 `error/error_type/status_code/resolved_url`，但执行历史 UI 只显示状态/备注/时间/链路，根因完全不可见。
- 无环境/Token 就绪检查：未选环境也允许执行，制造 325 条无意义失败记录。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 缺陷创建（不选处理人） | 422 + 崩溃 | HTTP 200 创建成功 | 本地/测试环境回归 |
| 前端 422 错误展示 | 崩溃 | toast 展示可读中文信息，页面不崩 | 单测 + 浏览器复测 |
| 执行历史根因可见 | 无失败原因列 | 每行含失败原因/HTTP 状态/失败阶段；历史 325 条同样可读 | API 返回 + UI |
| 计划执行预检 | 未选环境照常执行 | API 用例计划未选环境/无 base_url/缺变量时被拦截并给出明确提示 | 接口测试 + UI |
| 执行记录字段 | 仅 JSON | DB 独立列 status_code/error_type/error_message | 迁移 + 接口 |

## 3. 用户故事 + 验收标准

- As 测试人员, I want 不选处理人也能新建缺陷且不崩溃, so that 缺陷主写路径可用。
  - Given 打开新建缺陷弹窗 / When 不选处理人直接保存 / Then 缺陷创建成功并提示「缺陷已创建」，页面不崩溃。
  - Given 后端返回 422 / When 保存失败 / Then 弹窗内显示可读错误信息且弹窗不关闭、页面不崩溃。
- As 测试人员, I want 在计划详情直接看到每条执行失败的原因, so that 无需翻 JSON 即可定位。
  - Given 执行历史有失败记录 / When 查看「执行历史」Tab / Then 每行显示失败原因摘要、HTTP 状态、失败阶段。
  - Given 历史记录只有 actual_result JSON / When 查看 / Then 前端/后端解析回填显示，不丢字段。
- As 测试人员, I want 一键执行前先选择环境且后端强制预检, so that 不再产生 http:/// 这类无效执行。
  - Given 计划含 API 用例且未选环境 / When 点击「批量执行/一键执行」 / Then 前端提示先选环境，后端同样拦截并返回明确错误。
  - Given 环境无 base_url 或缺少用例引用的变量 / When 执行 / Then 被拦截并提示缺失项。

## 4. 技术考量

- DB：`test_execution` 增加 `status_code`(int, default 0)、`error_type`(str, default '')、`error_message`(text, default '')；Alembic 迁移 revision 挂在 `20260808_batch121_topo_edges`（当前单头），带 inspector 守卫（幂等）。
- 兼容：历史行新列为默认值，读取时若为空则从 `actual_result` JSON 回填解析（`error/error_type/status_code`）。
- 预检语义：仅当计划含 API 用例时强制环境；base_url 仅对相对路径端点必需；变量引用缺失（如 `${token}`）在环境变量中不存在时拦截。
- 前端：`client.ts` 错误提取链必须把数组型 `detail` 转可读字符串（修复对象渲染崩溃的根因）；执行历史表格加 3 列；环境选择器在计划详情头部。
- 风险：迁移需与模型同步（`AUTO_CREATE_TABLES` 可能掩盖错位，按 bug-guard 用 inspector 守卫）；前端 Select 空值用 sentinel（`'__none__'`），不用空串/0。
- 依赖：无新增依赖。

## 5. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main | 全部 | PR checks 全绿 + 审计通过 |
| 部署后回归 | 测试人员 | 缺陷创建/执行历史/预检三路径复测通过 |

## 6. 技能使用

- cameltv-bug-guard → 迁移幂等/错误提取链/Select sentinel/静态路由等避坑清单（已扫描）
- cameltv-ui-conventions → 执行历史表格与 Select 交互基线（Design 走查使用）
