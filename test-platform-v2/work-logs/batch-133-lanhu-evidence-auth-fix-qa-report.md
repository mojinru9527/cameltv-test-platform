# Batch 133 — 蓝湖证据采集会话失效/失败状态 QA 报告
> **QA (🔍)** | Date: 2026-08-10 | Verdict: PASS（发布建议 READY）

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 6（PRD 验收标准） | 6 | 0 | 0 |

## 可执行门禁
| 门禁 | 命令 | 退出码 | 结果 |
|------|------|:---:|------|
| 后端 F821 | `ruff check app --select F821` | 0 | All checks passed |
| 后端定向 | `pytest test_lanhu_evidence_auth.py` | 0 | 8 passed（418 分类 / Cookie 存储 / 证据流会话失败 / ai_service 不透传） |
| 后端全量 | `pytest -q` | 1 | **1297 passed / 3 failed**（lanhu-mcp 子模块未初始化环境基线，同 Batch 132）/ 3 skipped |
| 前端类型检查 | `npm run typecheck` | 0 | 通过 |
| 前端构建 | `npm run build` | 0 | built in 8.54s |
| 前端全量 | `npm test` | 0 | 109 文件 / 440 用例全过 |
| 浏览器验收 | Playwright（API mock） | 0 | `browser-acceptance.json` status=pass |
| 截图核验 | vision（qwen-vl） | 0 | 失败徽标 + 已结束（失败）+ 会话失效错误横幅 + 登录入口确认 |

## 逐条件验证
| 验收标准 | 结果 | 证据 |
|----------|:---:|------|
| 418 识别为会话失效并返回可读原因 | ✅ PASS | `_is_lanhu_session_expired` 覆盖 401/403/418；证据流返回"会话失效 + manual_action_required"；单测 3 条 |
| 失败不显示"已完成" | ✅ PASS | ai_service 不再把会话错误吞成"图片格式"兜底（单测）；前端失败任务 stage 显示"已结束（失败）"，浏览器断言 `falseDoneHidden` |
| 用户重新登录/更新 Cookie 后自动重试 | ✅ PASS | 新增 `/lanhu-evidence/cookie`（粘贴/清除）+ `/lanhu-evidence/login`（尽力登录）；Provider 自动使用已保存 Cookie；浏览器对话框保存 Cookie 走通 |
| 凭据安全 | ✅ PASS | 仅存 Cookie（data/lanhu_cookie.txt），密码不落库；login 尽力而为，缺失时明确回退"粘贴 Cookie" |
| 登录被风控拦截有兜底 | ✅ PASS | login 返回明确提示 + 粘贴 Cookie 兜底入口 |
| 回归无新增失败 | ✅ PASS | 前端 440/440；后端 1297 通过（3 失败为子模块环境基线） |

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 1 | P3 | 后端 3 个 lanhu/deploy 契约测试因 lanhu-mcp 子模块未初始化失败（环境基线） | `lanhu_mcp_server.py is_file` 为 False | 环境基线（CI 初始化子模块应通过） |
| 2 | P3 | lanhu-mcp 子模块 `extract_doc.py:22` 含明文蓝湖密码，建议清理（不在本批子模块范围） | 代码行 | 提示用户处理 |

## 发布建议
状态: **READY** · 必修复: 0 · 建议修复: 1（子模块明文密码清理）

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 6h / 实际 4h | 0/0/0/2 | 1 | 工具链 | 新 worktree 先 npm ci；子模块基线失败先确认环境再定性 |

**技能使用**: `cameltv-agent-team` / `cameltv-bug-guard`（异常分类与不吞错误）/ `cameltv-ui-conventions`（失败状态展示）/ `vision`。
