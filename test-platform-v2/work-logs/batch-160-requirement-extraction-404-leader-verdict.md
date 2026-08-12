# Batch 160 — Leader 判决（需求「功能拆分」404 热修）

> **Leader (🎯)** | Date: 2026-08-12 | Decision: APPROVED（待总确认 + CI 通过后合入）

- 根因清晰（envelope code=404 与 HTTP 404 混淆 + 拦截器丢 code），修复前端契约 + 回归测试。
- 风险：低（前端 API 层改动，后端不变）。
- 判决：APPROVED。

## 流程回写
| 发现 | 处理 | 落点 |
|------|------|------|
| 前端多处可能误用 response.status 判断 envelope 错误 | 拦截器统一附 code，调用方按 error.code 分支 | client.ts + cameltv-bug-guard（后续批次补充指引） |
