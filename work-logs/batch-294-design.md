# Batch 294 — Design / Dev

## 接口

```python
BaseAgent(llm: Callable[[system, user], str] | None, model=...)
  .run(input_text) -> dict     # parse → validate
  .parse_json(raw)             # 去 ```json 围栏；非对象/非法 JSON → AgentSchemaError

RequirementAgent(BaseAgent)    # key="A0"；AC 必须带 source_ref
run_agent(db, agent, project_id, input_text, run_id=None) -> dict
```

## 记录（agent_executions）

`id/project_id/run_id?/agent_key/status/model/input_text/output_json/error_text/
prompt_tokens/completion_tokens/started_at/finished_at/created_at`

成功与失败都落库；失败保留 `error_text`（类型 + 消息，截断 2000）。

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-294-1 | LLM 以 callable 注入 | 单测无需真实 Key/网络；生产由 ai_client 适配 |
| D-294-2 | 无 LLM 直接 `AgentUnavailable` | Key 无效 fail-closed，禁止静默降级 |
| D-294-3 | source_ref 强校验（非空） | AC 必须可追溯，防编造 |
| D-294-4 | 失败也写执行记录 | 审计/评测可统计失败率 |
| D-294-5 | 先只做 A0 | A1/A2 分批判，控制单批风险 |

## 文件

- `app/aiqe/models/agent.py`
- `app/aiqe/agents/base.py` / `requirement_agent.py` / `orchestrator.py`
- `alembic/versions/20261116_ta019_agent_executions.py`
- `tests/test_aiqe_requirement_agent.py`（6 条，含 30 样本集）
