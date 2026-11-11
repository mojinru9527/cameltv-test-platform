# Batch 291 — Design / Dev

## 结构

```text
scripts/node/cameltv_node/mcp/playwright_mcp/
  ├─ __init__.py
  └─ explorer.py     # assert_url_allowed / PlaywrightExplorer / handle_tool
```

## 流程

```text
handle_tool("explore_page", {url, actions})
  → assert_url_allowed(url, allowed_domains)
  → driver.goto(url)
  → 逐个 action（click/fill/wait_for/text）
      成功追加日志；失败记录 error 并 break
  → driver.capture_evidence()（DOM/A11y/screenshot/trace）
  → {url, ok, error, dom, a11y, actions[], artifacts[]}
```

## 域名规则

- 仅 `http/https`；
- 精确匹配或 `*.suffix`（含 suffix 本身）；
- 非 allowlist（含 `169.254.169.254`、`file://`）→ `DomainNotAllowed`，不调用 driver。

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-291-1 | driver 注入 | fake 可测，真实浏览器留给节点验收 |
| D-291-2 | 失败即停但保留已完成日志 | 首个失败可定位，后续不盲目执行 |
| D-291-3 | DOM/A11y 直接返回文本 | AI 可直接消费，不必先下载文件 |
| D-291-4 | 不做 MCP SDK 封装 | PoC 先验证安全边界与输出契约 |

## 文件

- `explorer.py`
- `tests/test_aiqe_playwright_mcp_explorer.py`（8 条）
