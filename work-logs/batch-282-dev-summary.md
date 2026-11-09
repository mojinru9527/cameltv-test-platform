# Batch 282（M1 / TA-008）— Dev Summary

> **部门**：🟦 Dev · **日期**：2026-11-10

## 变更

| 文件 | 说明 |
|------|------|
| `backend/app/api/v1/aiqe_runs.py` | 5 个只读端点 + SSE |
| `backend/app/aiqe/services/run_query_service.py` | 查询收敛（路由层禁 ORM） |
| `backend/app/schemas/aiqe_run.py` | Run/Event/Artifact Pydantic |
| `backend/app/api/v1/router.py` | 注册 router |
| `backend/tests/test_aiqe_run_api.py` | 6 条 API 测试 |
| `backend/tests/fixtures/route_inventory.json` | +5 路由（317→322） |
| `frontend/src/api/aiqeRuns.ts` / `types/aiqe.ts` | API/类型 |
| `frontend/src/pages/runs/{index,detail}.tsx` | 列表/详情 |
| `frontend/src/pages/runs/useRunEvents.ts` | SSE + 轮询降级 + seq 去重 |
| `frontend/src/router/index.tsx` | `/runs`、`/runs/:runId` |

## 验证

```text
pytest tests/test_aiqe_run_api.py        → 6 passed
pytest -q                                → 1398 passed / 43 skipped
npm run typecheck                        → 0
npm run build                            → 0
npm run lint                             → 0
npm test                                 → 123 files / 550 tests passed
quality_ratchet.py                       → PASS
```
