# Batch c165-2-entry-consolidation — QA 报告
> **QA (🔍)** | Date: 2026-08-13 | Verdict: PASS

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 4 | 4 | 0 | 0 |

## 可执行门禁
| 门禁 | 命令 | 结果 |
|------|------|------|
| 后端 F821 | `python -m ruff check app --select F821` | ✅ All checks passed |
| 后端导入 | `python -c "from app.main import app"` | ✅ import ok |
| Alembic 单头 | `python -m alembic heads` | ✅ 单 head `20260812_b164_sched_heartbeat` |
| 后端相关测试 | `pytest test_batch63_menu_catalog.py` | ✅ 6 passed |
| 前端 typecheck | `npm run typecheck` | ✅ exit 0 |
| 前端 build | `npm run build` | ✅ vite build 8.08s |
| 前端相关测试 | `vitest run CommandPalette/guestModuleCatalog/ProjectAccessBoundary` | ✅ 3 files / 33 tests passed |

## 逐条件验证
### C1: 项目管理/组织管理菜单隐藏
**变更文件**: backend/app/services/menu_service.py（HIDDEN_MENU_CODES）；backend/app/seed.py（注释两菜单 + tester/viewer 菜单移除）
| 检查项 | 结果 |
|--------|------|
| 存量库运行时过滤 `menu:project`/`menu:organization` | ✅ HIDDEN_MENU_CODES 含两项 |
| 新库不再生成两菜单 | ✅ seed 注释 + `test_c1652_project_organization_menus_removed_from_seed` 通过 |
| tester/viewer 角色菜单不含组织管理 | ✅ `_TESTER_MENUS`/`_VIEWER_MENUS` 已移除 |

### C2: 前端旧深链重定向
**变更文件**: frontend/src/router/index.tsx
| 检查项 | 结果 |
|--------|------|
| `/project` → `/my-projects` | ✅ `<Navigate to="/my-projects" replace />` |
| `/organizations` → `/my-projects` | ✅ `<Navigate to="/my-projects" replace />` |
| 旧懒加载组件注释，无未使用路由 | ✅ 编译通过 |

### C3: Command Palette 与访客目录收敛
**变更文件**: frontend/src/components/CommandPalette.tsx；frontend/src/layouts/guestModuleCatalog.ts
| 检查项 | 结果 |
|--------|------|
| Command Palette 用「我的项目」替代「项目管理」 | ✅ 单测断言 `/my-projects` 在、`/project` 不在 |
| 访客模块目录注释 `/project`、`/organizations` | ✅ guestModuleCatalog.test 通过 |

### C4: 无项目起步路径
**变更文件**: frontend/src/layouts/ProjectAccessBoundary.tsx
| 检查项 | 结果 |
|--------|------|
| 仅 `/my-projects` 为无项目起步路径 | ✅ 单测通过 |

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 无 | - | 本批未发现新增缺陷 | - | - |

## 发布建议
状态: **READY** | 必修复: 0 | 建议修复: 0

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1h vs 实际 0.5h | 0/0/0/0 | 0 | - | 入口收敛继续以“隐藏+重定向”最小改动为主 |

**技能使用**: cameltv-bug-guard → 菜单/路由副作用核对；cameltv-ui-conventions → 导航收敛基线。
