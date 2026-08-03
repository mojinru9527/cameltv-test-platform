# Batch 71 — QA 报告（内部收尾优化）

> **QA (🔍)** | Date: 2026-08-04 | Verdict: PASS

## 测试总览

| Slice | 通过 | 失败 | 阻塞 |
|:------|:----:|:----:|:----:|
| C70-3 登录限流环境化 | 5 | 0 | 0 |
| C69-3 AI 分批并发 | 1+1 回归 | 0 | 0 |
| C70-2 模板增强 | 1 E2E | 0 | 0 |
| C65-2 手册删除 | 1 | 0 | 0 |

## 可执行门禁

| # | 门禁 | 命令/方式 | 结果 |
|---|------|-----------|------|
| G1 | 后端单测 | `pytest test_login_rate_limit_config.py test_ai_generate_chunked.py test_batch48_requirement_acceptance.py` | PASS：37/37 |
| G2 | 后端 ruff F821 | `ruff check app/core/config.py app/core/rate_limit.py app/services/ai_service.py --select F821` | PASS |
| G3 | 前端 lint/typecheck/build | `npm run lint && npm run typecheck && npm run build` | PASS |
| G4 | 前端 Vitest 全量 | `npx vitest run` | PASS：87 文件 / 334 用例 |
| G5 | 登录限流实测 | dev 环境连续 12 次登录 | PASS：全部 200，无 429（放宽至 100/900） |
| G6 | 模板默认 E2E | Playwright：建模板 → 设为默认 → 徽标 | PASS |

## 逐条件验证

### C70-3 — 登录限流环境化
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 配置字段 | ✅ | `login_rate_limit_max` / `login_rate_limit_window_seconds`（生产默认 10/900） |
| 环境放宽 | ✅ | development/test → `max(配置, 100)`/窗口；单测 4 项 |
| 生产安全默认 | ✅ | production 返回 (10, 900) 不变 |
| 实测 | ✅ | dev 环境 12 连登全 200（原 10 次即 429） |

### C69-3 — AI 分批并发
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 并发控制 | ✅ | asyncio.Semaphore(2) 限并发；按块序合并（sorted by index） |
| 语义保持 | ✅ | 截断重试/块级失败告警/全部失败 ValueError 不变 |
| 单测 | ✅ | 3 块 45 FP → 3 次调用、6 条合并、编号唯一 |

### C70-2 — 报告模板增强
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 设为默认 | ✅ | 行内按钮 → `updateTemplate({is_default:true})`；E2E 徽标出现 |
| 章节启用 | ✅ | 编辑对话框章节勾选 → 保存 sections |

### C65-2 — 过时手册删除
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 删除 | ✅ | `test-platform-v2/docs/生产测试平台固定配置与双VPN切换验收手册.md` 已删除 |
| 引用清理 | ✅ | 3 处活文档 related/链接更新（运维/执行器隔离/Batch57 操作单）；历史 plans/work-logs 保留 |

## 发布建议

状态: **PASS**。四项内部收尾完成；生产安全默认不变；回归无新增失败。
