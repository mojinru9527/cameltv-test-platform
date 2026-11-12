# AIQE B 线（自测 / Dogfood）证据

> 日期：2026-11-12 · 环境：隔离 Test 实例（与生产库/容器分离）
> 结论：**服务层自测全部通过**；AI 链路通过；UI/真机未纳入本证据。

## 1. 环境

| 项 | 值 |
|----|----|
| Test UI | `http://127.0.0.1:18080`（服务器本地） |
| Test API | `http://127.0.0.1:18000` |
| 数据库 | 独立 `aiqe_test`（head `20261123`） |
| 镜像 | `release-m12-20261112` |
| AI | DeepSeek `deepseek-v4-flash`，`AI_ENABLED=true` |

## 2. 自测结果

| # | 自测项 | 结果 | 说明 |
|---|--------|:----:|------|
| 1 | TestRun 创建/完成 | PASS | outcome=PASS 持久化 |
| 2 | 缺陷草稿（步骤/证据/AC） | PASS | 一键盘转缺陷 |
| 3 | 一键回归 | PASS | 关联 verification_run |
| 4 | 质量门禁 | PASS | P0 全 PASS → PASS |
| 5 | 噪音规则创建/删除 | PASS | 90 天默认 |
| 6 | Execution Profile | PASS | core_isolated |
| 7 | Artifact 存储 | PASS | LocalFS put/read/delete 字节一致 |
| 8 | Workflow 审批 | PASS | approval_status=approved |
| 9 | DAG 调度 + ExecutionJob | PASS | 2 节点串行，2 个 Job，Run=PASS |
| 10 | 事件读取（SSE 底层） | PASS | `list_events` 正常（该 Run 无事件，返回 0） |
| 11 | MCP Gateway | PASS | 7 工具，`get_run` 返回 COMPLETED |
| 12 | A0→A2→A3 | PASS | 真实 LLM；约束 driver 后 A3 pending 8 节点 |

## 3. AI 费用

| 项 | 值 |
|----|----|
| 调用轮次 | probe + 单样本 + 3 轮 Agent |
| Token 总量 | 约 **15.6k** |
| 估算费用 | **< 0.2 元**（预算 20 元） |
| 预算状态 | 未超限 |

## 4. 已知边界

- 事件读取的 Run 无事件，`events=0`；如需非空 SSE，补 `append_event` 后再验；
- Test API 登录限流（10 次/15 分钟）会阻断批量 HTTP 检查；服务层自测不受影响；
- Web 登录入口有反爬层，已按要求跳过；
- 真机停在登录弹窗（国家码 +61 未切 +86），未纳入本证据。

## 5. 复现命令（服务层）

```bash
# 在 aiqe-test-backend 容器内：
python /tmp/dogfood_self.py            # Run/缺陷/回归/门禁/规则/Profile
python /tmp/dogfood_artifact.py        # Artifact 存储
python /tmp/dogfood_dag.py             # Workflow/审批/DAG/ExecutionJob
python /tmp/dogfood_sse_mcp_service.py # 事件读取 + MCP Gateway
```
