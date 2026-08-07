# Batch 118 — QA 报告（追踪器卫生清理 + C109-1 收尾 + C102-3/4 + C117-1）

> **QA (🔍)** | Date: 2026-08-07 | Verdict: **PASS（READY）**

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 本批验收项 4（C109-1/C102-3/C102-4/C117-1） | 4 | 0 | 0 |
| 卫生核对项 13 | 13 关闭 | 0 | 0（C114-1/C104-3/C105-3/C105-4/C106-2 转下批） |

## 可执行门禁（命令 + 退出码）

| 门禁 | 命令 | 结果 |
|------|------|------|
| 后端 F821 | `ruff check app --select F821` | ✅ All checks passed |
| Alembic 单头 | `alembic heads` | ✅ 1 head（20260807_batch115_tc_depends） |
| app 导入 | `python -c "from app.main import app"` | ✅ OK |
| 后端受影响 pytest | `pytest test_requirement_modules_direct_build test_production_diff test_batch48_requirement_modules test_api_task_worker test_apitest_tasks test_requirement` | ✅ 57 passed |
| 前端 typecheck | `npm run typecheck` | ✅ |
| 前端 build | `npm run build` | ✅ built in 10.45s |
| 前端受影响 vitest | `npm test -- --run src/pages/requirement` | ✅ 5 files / 16 passed |
| C 追踪器 | `audit-cconditions.ps1 -RequireLatestBatch` | ✅ 0 hard errors / 0 warnings（Closed=176） |
| 避坑扫描 | `scan-common-bugs.ps1` | ⚠️ 3 HARD 均为本批未触碰历史文件（ai_service.py:324 / xhr_capture_service.py:74,95），记豁免转后续批次；214 WARN 已复核 |

> 前端依赖说明：worktree 前端 node_modules 复用主仓库 node_modules（junction）执行本地门禁；PR CI 将做干净安装全量回归。

## 逐条件验证

### C109-1（生产收尾）— ✅ PASS
**证据**: `evidence/batch-118/c1091-invite-link-summary.json` + 截图 2 张
- PLATFORM_FRONTEND_URL=https://cameltv-test-platform1.vercel.app ✅
- SEED_DEMO_USERS=false 行为生效：batch 112-117 多次自动部署后生产库仍 3 用户/0 演示账号；登录/注册页无演示入口 ✅
- 邀请链接端到端：https 200 → 注册页提示「你正被邀请加入一个项目」→ 注册成功跳转 /my-projects → 自动入项目 1（role 2）+ 个人组织 + 项目组织；项目邀请 token 消耗 1；平台邀请码被豁免（used_count=0）✅
- 复测后演示账号仍 0 ✅

### C102-3（模块树直建）— ✅ PASS
**变更文件**: `backend/app/services/knowledge/module_extractor.py`（build_module_tree_from_document）、`backend/app/schemas/release_bundle.py`（BuildFromDocumentRequest）、`backend/app/api/v1/requirement_modules.py`（POST /build-from-document）
- 直建路径（extraction_raw）✅ / content markdown 兜底 ✅ / 自动建发布包 ✅ / 指定发布包 ✅ / 404（文档不存在/跨项目）✅
- 单测 5/5（test_requirement_modules_direct_build.py）

### C102-4（差异标注）— ✅ PASS
**变更文件**: `backend/app/services/knowledge/production_diff_service.py`、`backend/app/schemas/release_bundle.py`（ProductionDiffRequest）、`backend/app/api/v1/requirement_modules.py`（POST /production-diff）
- new/matched/missing 三类标注 ✅ / 匹配归一化与相似度阈值 ✅ / 空模块树 warning ✅ / 发布包 404 ✅
- 单测 4/4（test_production_diff.py）
- 前端展示本批豁免（无模块树页面上下文，转下批 UI 迭代，见设计规范 §5）

### C117-1（覆盖缺口前端展示）— ✅ PASS
**变更文件**: `frontend/src/types/index.ts`（CoverageReport）、`frontend/src/pages/requirement/AiResultModal.tsx`（覆盖矩阵/缺口 Tab）
- 覆盖率徽标 + 已覆盖/总功能点 + 缺口列表 + 矩阵表 ✅ / 无报告时隐藏 Tab ✅
- vitest 4/4（含 Tab 切换：Radix Tabs 需 mousedown 激活，测试已适配）

### 卫生核对（13 项关闭）
C103-1~7、C102-2、C102-5、C110-3、C101-1、C113-1、C114-2 —— 全部以生产实测/代码锚点/既有 evidence 交叉核对后关闭，见 `evidence/batch-118/hygiene-audit-summary.json`。

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| B118-1 | P2 | scan-common-bugs 3 个 HARD（except: pass）位于本批未触碰文件（ai_service/xhr_capture_service） | scan 输出 | 转下批修复（豁免登记） |
| B118-2 | P3 | C109-1 复测账号 c1091_check_215243 保留在生产（id=10，入项目 1） | 证据 JSON | 保留用于回归；如需清理运营后台停用 |
| B118-3 | P3 | Radix Tabs 在 jsdom 需 mousedown 激活（测试适配，非产品缺陷） | AiResultModal.test | 已解决 |

## 发布建议

状态: **READY**。必修复: 0；建议修复: B118-1（下批）。

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 2d / 实际 1d | 0/0/1/2 | 3 | 工具链 | 断言先确认本仓 404 约定与文本匹配语义再写测试；PowerShell 写长行代码先校验语法 |

**技能使用**: `cameltv-agent-team`（六部门流水线）、`cameltv-bug-guard`（避坑）、`cameltv-ui-conventions`（前端规范）、`playwright`（C109-1 端到端）。
