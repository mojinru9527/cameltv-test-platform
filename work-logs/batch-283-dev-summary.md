# Batch 283（M2 / TA-009）— Dev Summary

> **部门**：🟦 Dev · **日期**：2026-11-10

## 文件

| 文件 | 说明 |
|------|------|
| `backend/app/aiqe/services/workflow_validator.py` | 校验器 + checksum + 结构化错误 |
| `backend/tests/test_aiqe_workflow_validator.py` | 16 条单测（合法/环/悬空/变量/重试/断言/edge/checksum） |

## 行为

- 合法样例（M1 规格 §6.1 的 4 节点样例）通过；
- 环、悬空依赖/变量、未注册 driver/capability、非幂等写重试、缺 expected 断言全部拒绝；
- 一次返回全部 issue（`issues` 列表）；
- checksum 与键顺序无关、内容变化即变化。

## 验证

```text
pytest tests/test_aiqe_workflow_validator.py  → 16 passed
pytest -q                                      → 1414 passed / 43 skipped
quality_ratchet.py                             → PASS
```
