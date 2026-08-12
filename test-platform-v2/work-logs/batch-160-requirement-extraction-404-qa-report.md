# Batch 160 — QA 报告（需求「功能拆分」404 热修）

> **QA (🔍)** | Date: 2026-08-12 | Verdict: PASS | Mode: light

## 门禁
| 项 | 结果 |
|----|------|
| typecheck | ✅ 0 |
| build | ✅ built in 10.25s |
| vitest 全量 | ✅ 113 files / 460 tests（新增 5） |
| 受影响测试 | ✅ client-422-detail ×5 + requirement ×14 |

## 逐项验证
| 检查项 | 结果 |
|--------|------|
| 拦截器业务错误携带 code=404 | ✅ 单测（HTTP 200 + code=404 → Error{message, code:404}） |
| getOrCreateExtraction code=404 回退 POST /extract | ✅ 单测 |
| 已有结果不重复创建 | ✅ 单测 |
| 非 404 错误原样抛出不创建 | ✅ 单测（403/500/网络超时） |

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 实际约 0.5h | 0/1/0/0 | 0 | envelope code 与 HTTP status 混淆 | 前端处理业务错误统一看 `error.code`，勿用 response.status |
