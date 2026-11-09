# P0-1 阻塞：生产 AI Key 全部 401，且无可用新 Key

> 状态：**BLOCKED**（2026-11-09 22:10）
> 影响：AI 用例生成 / 需求拆分 / 知识向量化不可用；M0 Gate 不能通过。

## 1. 实测结果

| 探测对象 | 结果 | 证据 |
|---------|------|------|
| 生产 `ai_provider` 3 条 | DeepSeek 官方 / 验收项目 / 官方 均 **HTTP 401** | 容器内脚本 `/tmp/p01_probe.py`，输出 `providers 3 … 401 … 401 … 401` |
| 生产 env `AI_API_KEY` | **未设置**（`ENV_KEY absent`） | 同上 |
| 本地候选 Key（backend/.env、deploy/.env、container.env、railway-vars.json） | 3 个唯一 Key 全部 **401** | 本地探测脚本（只打印状态码） |
| 本地 Agent 配置（`.claude/providers/deepseek.json` 等） | 1 个 Key，**401** | 同上 |

**结论**：现有 4 把（生产 3 条 provider + 本地）DeepSeek Key 全部失效，且没有可用的新 Key。

## 2. 为什么不能自动完成轮换

- DeepSeek 控制台创建 API Key 必须登录账号（可能含短信/验证码），仓库与本地未找到账号凭据；
- 已检索 `Desktop / Documents / Downloads / F:\CamelTv / F:\CamelTv-safe-backup` 等位置的 `服务器/连接/密码/账号/ssh` 文本，未发现 DeepSeek 控制台账号；
- SSH 服务器连接**可用**（`~/.ssh/cameltv_tencent_lighthouse`），但只能拿到已失效的旧 Key。

## 3. 需要用户提供（二选一）

**A. 新的 DeepSeek API Key（推荐，最快）**

提供 1~4 个有效 Key（`sk-…`），我按下面的步骤完成轮换与验证。

**B. DeepSeek 控制台账号访问**

提供可登录 console.deepseek.com 的方式（账号密码 + 验证码处理），我创建 4 把新 Key 并入库。

## 4. 拿到新 Key 后的执行步骤（已就绪）

1. 在容器内用 `app.core.cipher.encrypt_value` 重新加密，更新 `ai_provider` 三行（或新增第 4 行）；
2. 同步 `production.env` 的 `AI_API_KEY/AI_API_BASE_URL/AI_MODEL`；
3. 重启 backend 容器（不动 PG）；
4. 真实发一次 `requirement → cases` LLM 调用（或最小 chat），确认 `model_usage_ledger` 新增一行；
5. 写 `P0-1-ai-key-rotation.json`（status=pass + checked_at + 调用日志），守卫 P0-1 转绿。

## 5. 关联

- 13 号 §0 P0-1
- `work-logs/platform-simplification-production-eval-20261007.md` §3（Key 401 历史）
