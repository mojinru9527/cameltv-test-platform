# Batch 169 — QA 报告
> **QA (🔍)** | Date: 2026-08-13 | Verdict: PASS

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 2 个 PM 任务 | 2 | 0 | 0 |

## 可执行门禁（实测命令与退出码）
| 门禁 | 命令 | 结果 |
|------|------|------|
| 后端 F821 | `python -m ruff check app --select F821` | ✅ exit 0 |
| 后端导入 | `python -c "from app.main import app"` | ✅ IMPORT_OK |
| Alembic 单头 | `python -m alembic heads` | ✅ 单头 |
| 后端全量回归 | `python -m pytest -q` | ✅ **1427 passed, 3 skipped**（submodule 初始化后 lanhu 12/12） |
| 前端 typecheck/lint/build | npm 三件 | ✅ 均 exit 0 |
| 前端全量单测 | `npm test` | ✅ 113 files / 458 passed |

## 逐条件验证
### Task 1 execute-all 异步化（C168-2）
- `ExecuteAllBody.async_mode=true` → BackgroundTasks 后台执行、立即返回。
- 真实数据验证：本地新代码+生产库，plan#13 含 2 条 UI 用例，请求 2.26s 返回 `{"async":true}`，后台完成 pending 2→0，执行记录落库。
- 单测：async 返回立即 + 参数透传；sync 旧行为不变。

### Task 2 UI 执行超时可配置 + 编译稳定
- `settings.ui_run_timeout_seconds` 默认 90（env 可覆盖）；TimeoutExpired 文案含秒数。
- SYSTEM_PROMPT 禁用 networkidle，要求默认导航 30s/DOM 15s、等待显式 timeout。
- 单测：提示词断言 + 超时文案断言。

## 缺陷列表（本批发现）
| # | 严重级 | 描述 | 状态 |
|---|--------|------|------|
| 1 | P2 | 生产 www.camel1.tv/login 返回 404、REGISTER 无交互入口 | 外部阻塞（C169-1） |
| 2 | P3 | 本地 npx 单机运行某些 spec 时未输出 JSON 报告 | 记录，不影响异步化验证 |

## 发布建议
状态: **READY** | 必修复: 0 | 建议修复: 0

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 4h / 实际约 3h | 0/0/1/1 | 1 | 外部登录入口未知 | 登录态复测先确认入口再排批 |

**技能使用**: cameltv-bug-guard → BackgroundTasks/旧契约兼容；diagnose → 网关 300s 定位。
