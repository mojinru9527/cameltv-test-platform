---
name: a5-change-impact
description: A5 变更影响 Agent——PR diff 文件 → 影响域 + 候选回归并集；公共权限/登录变化强制 auth-suite + smoke-suite，漏选即拒绝。
---

# A5 Change Impact Agent

## 输入

```json
{"files": ["backend/app/api/v1/auth.py", "frontend/src/pages/live/index.tsx"]}
```

## 输出

```json
{
  "impacted_areas": ["auth", "live"],
  "candidate_suites": ["auth-suite", "live-suite", "smoke-suite"],
  "forced_suites": ["auth-suite", "smoke-suite"],
  "rationale": "登录入口变更 + 直播页变更"
}
```

## 规则

1. `auth/login/permission/rbac/token/session` → 强制 `auth-suite + smoke-suite`；
2. 候选并集必须包含所有强制 suite；
3. 未知变化默认 `smoke-suite`（保守）；
4. 空 diff 拒绝。

## 安全边界

- 不直接执行回归，只给 suite 选择；
- 强制 suite 不可被 LLM 省略。
