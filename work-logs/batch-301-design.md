# Batch 301 — Design / Dev

## Skill 文件

`.claude/skills/noise-hint-agent/SKILL.md`：触发时机、输入/输出 JSON、规则、广告抖动示例、
安全边界（只出草案、不关缺陷、证据可定位）。

## 参考实现

```python
NoiseHintAgent(llm).analyze(failure_context) -> {
  "hints": [{"hint": str, "suspected_factor": "AD_JITTER|FEATURE_FLAG|CONCURRENT_RUN|ENV_DRIFT|DATA_LEAK|UNKNOWN",
             "evidence_refs": ["artifact:…"]}],
  "human_review_required": true,
  "auto_close_defect": false,
}
```

## 校验

| 规则 | 处理 |
|------|------|
| hints 数量 ∉ [1,3] | schema 拒绝 |
| evidence_refs 为空 | 拒绝 |
| 证据前缀非法 | 拒绝 |
| auto_close=true / human=false | 拒绝 |
| 证据不足 | 允许 UNKNOWN，但需 hint + 引用 |

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-301-1 | Skill 文档 + Python 参考实现 | 既可被人/Agent 使用，也可被测试验证 |
| D-301-2 | 证据前缀白名单 | 强制引用可定位证据，防“空口归因” |
| D-301-3 | 只输出 hint，不写 Run/Defect | 安全边界 |
| D-301-4 | UNKNOWN 需证据引用 | 即使是“不知道”也要给依据 |

## 文件

- `.claude/skills/noise-hint-agent/SKILL.md`
- `app/aiqe/agents/noise_hint_agent.py`
- `tests/test_aiqe_noise_hint_agent.py`（8 条）
