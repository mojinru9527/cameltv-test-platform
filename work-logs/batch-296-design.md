# Batch 296 — Design / Dev

## 接口

```python
WorkflowPlannerAgent(llm, registered_drivers=..., registered_capabilities=...)
  .plan(assessment, scenario_key=None) -> {
      "workflow": {schema_version, scenario_key, nodes, edges, run_policy},
      "rationale": str,
      "approval_required": True,
      "approval_status": "pending",
  }
  .dependencies_match(workflow, expected) -> bool
  .ensure_executable(workflow_record) -> None | WorkflowNotApproved
```

## 校验链

```text
parse JSON → Pydantic（WorkflowPlan）
→ approval_status 必须 pending、approval_required 必须 True
→ validate_workflow（driver/capability 注册表 + 环/依赖/变量/断言）
```

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-296-1 | 复用 batch-283 validator | 单一事实源，避免两套规则 |
| D-296-2 | 规划器禁止自批 | 审批必须走人工/流程 |
| D-296-3 | 标注样本用依赖集合比对 | 20 个工作流可确定性命中 |
| D-296-4 | default driver 集固定 | PoC 不依赖 DB 注册表 |

## 文件

- `app/aiqe/agents/workflow_planner_agent.py`
- `tests/test_aiqe_workflow_planner_agent.py`（7 条，含 20 工作流）
