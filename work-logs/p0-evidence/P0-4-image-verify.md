# P0-4 控制面镜像验证（本地构建，2026-11-09 23:20）

> 目标：用合并后的 Dockerfile 构建后端镜像，证明**镜像内无 Chromium**，且 `/uitest` 走节点。

## 1. 构建

```bash
docker build \
  --build-arg HTTP_PROXY=http://host.docker.internal:7688 \
  --build-arg HTTPS_PROXY=http://host.docker.internal:7688 \
  -t cameltv-tp-backend:b277b4 \
  -f test-platform-v2/backend/Dockerfile .
```

- 镜像：`cameltv-tp-backend:b277b4`
- ID：`sha256:de4d963bf7eeb939a3f91160d4375e8586aa9192ac4a2cfc42a7ac1843e9748c`
- 大小：811,859,174 bytes（≈812 MB）

## 2. 无 Chromium 验证

```bash
docker image inspect cameltv-tp-backend:b277b4 --format '{{.Id}} {{.Size}}'
docker run --rm --entrypoint sh cameltv-tp-backend:b277b4 -c \
  "command -v chromium || command -v chromium-browser || command -v google-chrome || true
   find / -maxdepth 6 \( -iname '*chromium*' -o -iname 'chrome' -o -iname 'headless_shell' \) -not -path '/proc/*' 2>/dev/null | head -5"
```

结果：

```text
sha256:de4d963bf7eeb939a3f91160d4375e8586aa9192ac4a2cfc42a7ac1843e9748c 811859174
（chromium/chrome 查找：无输出）
FIND_DONE
```

镜像 ENV：

```text
CONTROL_PLANE_BROWSER_ENABLED=false
UITEST_EXECUTION_MODE=node
（无 PLAYWRIGHT_BROWSERS_PATH）
```

## 3. /uitest 走节点

见 [P0-4-local-e2e.md](P0-4-local-e2e.md)：`ExecutionJob(kind=ui)` → `cameltv-node up --once` →
真实 Chromium 1/1 pass → 证据上传 → `UiTestRun.status=done`。

## 4. 构建期发现的既有缺口（非本批引入）

1. **Dockerfile `RUN --mount ... && cd` 语法错误**：本批已修（`RUN --mount ... cd ...`）；
2. **main 缺 `test-platform-v2/deploy/aitde-runtime/scripts/start-worker.sh`**（Dockerfile 引用）：
   该文件只在 AITDE 工作分支存在；本次构建临时从 `F:\CamelTv` 补入，**未随本批提交**。
   需单独确认该文件应归 main 还是移除该 COPY。

## 5. 生产复核

部署窗口用同一 Dockerfile 重建镜像后，重跑第 2 节命令并把 digest 写入
`P0-4-control-plane-no-browser.json`（覆盖本地 digest）。
