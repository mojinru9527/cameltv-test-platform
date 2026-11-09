# P0-4 控制面无浏览器（本地验证，2026-11-09 22:5x）

> 结论：**代码侧开关与降级已就绪**；控制面镜像构建因网络/子模块受限未能在本机完成，
> `docker image inspect` 证据留到发布窗口（同一次构建）。

## 1. 已实现

| 能力 | 行为（`CONTROL_PLANE_BROWSER_ENABLED=false`） |
|------|---------------------------------------------|
| `/uitest` local 模式 | run 直接 failed，错误提示改用 `UITEST_EXECUTION_MODE=node` |
| `playwright_executor`（计划执行/Playground 复用） | `_fail_run` 明确报错，不启动 subprocess |
| `/ui-tests/capture`（XHR 采集） | HTTP 503「页面采集需迁移到节点」 |
| 蓝湖证据截图 | `CaptureResult.error` 明确报错，不裸抛、不伪造成功 |
| Playground `execute_spec` | HTTP 503「需迁移到节点」 |

## 2. Dockerfile

- 删除 `./node_modules/.bin/playwright install --with-deps chromium` 与 `python -m playwright install chromium`；
- `npm ci --ignore-scripts`（只装 `@playwright/test` 包，不下载浏览器）；
- runtime ENV 增加 `CONTROL_PLANE_BROWSER_ENABLED=false`、`UITEST_EXECUTION_MODE=node`；
- 静态校验：`rg "playwright install" test-platform-v2/backend/Dockerfile` → **0**。

## 3. 本地验证记录

| 检查 | 命令 | 结果 |
|------|------|------|
| 门禁单测 | `pytest tests/test_b277b4_browserless_gate.py` | ✅ 7 passed |
| 契约单测 | `pytest tests/test_b277b_ui_node_dispatch.py` | ✅ 12 passed |
| 本地 `/uitest` node E2E | 见 `P0-4-local-e2e.md` | ✅ run done，1/1 pass |

## 4. 未完成：镜像构建证据

本机 `docker build` 需要在构建期 `git clone` 子模块 `lanhu-mcp` 与访问 npm/PyPI；
当前环境 `github.com:443` 不可达（本地代理 127.0.0.1:7688 未运行），子模块无法拉取，镜像构建被阻塞。

发布窗口内应执行（服务器/有网构建机）：

```bash
docker build -t cameltv-tp-backend:<tag> -f test-platform-v2/backend/Dockerfile .
docker run --rm --entrypoint sh cameltv-tp-backend:<tag> -c \
  "command -v chromium || command -v chromium-browser || command -v google-chrome || find / -maxdepth 4 -iname '*chromium*' -o -iname 'chrome' | head"
# 期望：无输出
docker image inspect cameltv-tp-backend:<tag> --format '{{.Id}} {{.Size}}'
```

同时确认容器内 `CONTROL_PLANE_BROWSER_ENABLED=false`、`UITEST_EXECUTION_MODE=node`。

> 在真实生产节点跑通一次 `/uitest`（非本机）后，再写 `P0-4-control-plane-no-browser.json`。
