# Batch PRD — AI provider/shadow freeze (PR-07)

mode: light
豁免理由：本批次只新增架构守卫，确认普通测试执行链不再读取 AiProvider/default_model 或调用 ai_service；无新行为。

## Acceptance
- API/Plan/Campaign/AITDE execution paths contain no platform LLM tokens.
- Provider and shadow remain ops/evaluation-only.
