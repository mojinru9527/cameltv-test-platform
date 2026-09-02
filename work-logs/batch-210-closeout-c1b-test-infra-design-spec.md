# Batch 210 — 收尾 — Design Spec
> **Design (🎨)** | Date: 2026-09-02

## 决策
| 决策 | 内容 |
|------|------|
| D1 test-infra | lanhu 相关测试若 `lanhu-mcp/lanhu_mcp_server.py` 不存在 → `pytest.skip("lanhu-mcp submodule not initialized")`；notification 测试补模型注册。 |
| D2 C1b adapter | `browser/driver.BrowserDriver` 已实现 IR 执行；`drivers.ensure_browser_runner()` 检测 `playwright` 导入与 BrowserDriver 构造，可用则 `register_browser_runner` 包装（回调签名 (ctx, db, seq)），不可用保持 BLOCKED 并让 blocked step 带 `browser_capability=False`。 |
| D3 C2b | materialize 无 observation 匹配时：若 plan 命令数==1 且命令 driver in {api,data}，按 oracle_type 默认绑定（DB→DB_COLUMN、API→API_JSONPATH、UI→UI_TEXT、EVENT→EVENT_FIELD、LOG→LOG_PATTERN）指向该命令 id；>1 命令不臆测。 |

## 兼容性
- lanhu/deploy 测试改为条件跳过，不影响 CI（CI 有子模块仍跑）。
- browser BLOCKED 仍默认（无真实 Playwright 环境），仅行为更可观测。

## 签核
通过。
