# Batch 150 — QA 报告（请求缓存/防抖/退避 + mindmap 聚合）

> **QA (🔍)** | Date: 2026-08-11 | Verdict: PASS

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 1 (C147-5) | 1 | 0 | 0 |

## 可执行门禁
| 门禁 | 命令 | 结果 |
|------|------|------|
| 前端 typecheck | `npm run typecheck` | ✅ |
| 前端 build | `npm run build` | ✅ |
| 前端全量 vitest | `npx vitest run` | ✅ 113 files / 455 tests（含新增 5） |
| 后端 ruff | `python -m ruff check app/ --select F821` | ✅（无后端改动） |
| alembic heads | `python -m alembic heads` | ✅ 单头 |
| Network 冒烟 | Playwright SPA 导航 | menus/env/domains ×1；mindmap taxonomy |

## 逐条件验证

### C147-5 请求冗余修复
**变更文件**: client.ts、api/auth.ts、api/environment.ts、api/testcase.ts、hooks/useDebouncedValue.ts、hooks/usePerfWebSocket.ts、pages/defect/index.tsx、pages/integration/index.tsx、pages/mindmap/*

| 检查项 | 结果 | 说明 |
|--------|------|------|
| menus/environments/domains 会话缓存+去重 | ✅ | 冒烟 ×1（基线 53/6/4）；单测 4/4 |
| CRUD 后缓存失效 | ✅ | clearApiCache 前缀清理（代码 + 单测） |
| 搜索 300ms 防抖 | ✅ | defect 接入 useDebouncedValue；单测 1/1 |
| 轮询指数退避 | ✅ | 500ms→30s，有数据复位（setTimeout 链） |
| mindmap 服务端 taxonomy 聚合 | ✅ | 冒烟 0 次 page_size=10000，改用 taxonomy；页面渲染正常 |
| integration 去 page_size=1 探针 | ✅ | 2 处改 fetchTestCaseStats |

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 无 | - | - | - | - |

## 发布建议
状态: **READY**   必修复: 0   建议修复: 0

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 4h vs 实际 3h | 0/0/0/0 | 1 | 测试 mock 未同步新导出 | 改 client 导出后同步所有 vi.mock('@/api/client') |

**技能使用**: cameltv-bug-guard（重复请求/清理）；playwright-skill（Network 冒烟）
