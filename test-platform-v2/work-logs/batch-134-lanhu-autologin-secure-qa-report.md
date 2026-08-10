# Batch 134 — lanhu 自动登录 + 安全清理 QA 报告
> **QA (🔍)** | Date: 2026-08-10 | Verdict: PASS（发布建议 READY）

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 5（PRD 验收标准） | 5 | 0 | 0 |

## 可执行门禁
| 门禁 | 命令 | 退出码 | 结果 |
|------|------|:---:|------|
| 后端 F821 | `ruff check app --select F821` | 0 | All checks passed |
| 后端导入 | `python -c "from app.main import app"` | 0 | import ok |
| 后端定向 | `pytest test_lanhu_login_hook.py test_lanhu_evidence_auth.py test_lanhu_provider.py` | 0 | 28 passed（含登录钩子 2 + 证据流 8 + provider 18） |
| 后端全量 | `pytest -q`（子模块已初始化） | 0* | **1309 passed**；唯一失败 `test_pinned_runtime_without_optional_login_symbols` 为预期行为变化（本批给子模块加了 login），已更新为 `test_pinned_runtime_provides_login_hooks` 并重跑通过 |
| 子模块编译 | `python -m py_compile lanhu_mcp_server.py` | 0 | 语法通过 |
| 明文密码扫描 | 代码扫描 | - | 跟踪代码无新增明文凭据；本地 extract_doc.py 明文已改环境变量 |

* 全量在更新该测试后即为全绿（子模块在本 worktree 已初始化；此前 batch-132/133 的 3 个失败为子模块未初始化环境基线，本批不适用）。

## 逐条件验证
| 验收标准 | 结果 | 证据 |
|----------|:---:|------|
| lanhu-mcp 提供 lanhu_login/_save_cached_cookie | ✅ PASS | 钩子测试导入验证 callable；无凭据返回空串；_save_cached_cookie 落盘 |
| 后端 runtime.login 可调用 | ✅ PASS | test_pinned_runtime_provides_login_hooks 断言 login/save_cookie callable |
| 无凭据/失败回退 | ✅ PASS | lanhu_login("") 返回空串不抛异常（单测） |
| 无新增硬编码凭据 | ✅ PASS | 扫描无明文；本地 extract_doc.py 改 env |
| 子模块指针可拉取 | ✅ PASS | 子模块 main/分支已推送（3cfd2ef），CI 可 fetch |

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 1 | P3 | 既有测试假设 pinned 子模块无 login 符号（本批预期变化） | 已更新为提供 login 钩子断言 | 已修复 |

## 发布建议
状态: **READY** · 必修复: 0 · 建议修复: 0（生产需 Playwright chromium 可用，自动登录为尽力而为）

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 5h / 实际 3h | 0/0/0/1 | 1 | 技术债 | 新增能力前先看既有契约测试是否假定其缺失 |

**技能使用**: `cameltv-agent-team` / `cameltv-bug-guard`（无硬编码密钥/异常兜底）。
