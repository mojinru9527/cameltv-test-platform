# Batch 159 — Leader 判决（蓝湖提取失败热修）

> **Leader (🎯)** | Date: 2026-08-12 | Decision: APPROVED（待总确认 + CI 通过后合入）

- 根因清晰（lanhu-mcp 30s 单请求超时/无整体超时 + 空错误被吞）、修复有界（超时+重试+透出）。
- 风险：低（provider 内部加固，不改 MCP/接口契约）。
- 判决：APPROVED。

## 流程回写
| 发现 | 处理 | 落点 |
|------|------|------|
| 外部依赖异常 str 为空会吞成通用文案 | 统一 `str(e) or type(e).__name__` | 建议写入 cameltv-bug-guard（外部 I/O 错误链） |
| 旧版 lanhu-mcp 无整体超时 | provider 侧 wait_for + 重试 | lanhu_provider.py |
