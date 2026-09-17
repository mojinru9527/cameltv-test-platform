# Batch 252 — Design 规范（发布链路收口）

> **🎨 Design** | Date: 2026-09-17 | 无 UI 变更；本规范覆盖**构建/发布接口契约**

## 1. runner 镜像的 Node 供给契约（C248-8）

```
[runner 阶段]
  apt: ca-certificates curl git ffmpeg openssh-client libgl1 libglib2.0-0 libxcb1 libx11-6 libxext6 libsm6 libice6
   ↓ 禁止：curl <url> | bash -        （管道吞失败 → 静默降级，历史缺陷）
   ↓ 必须：curl -fsSL --retry N -o /tmp/nodesource_setup.sh <url> && bash /tmp/nodesource_setup.sh
   ↓ 必须：apt-get install nodejs
   ↓ 必须断言（同一 RUN 内）：
        node -e "…process.versions.node 必须是以 '22.' 开头…"
        npm --version >/dev/null
   ↓ 断言失败 → 该层立即失败（不允许进入下一步才报 npm: not found）
```

**契约含义**：runner 阶段的 Node 供给是"要么装对、要么立刻炸"，不存在中间态。
断言写在**安装层的同一个 RUN**里，保证缓存也带着这个保证。

## 2. 沿用镜像的核对接口（C249-5）

```
输入: 镜像 tag + 部件(backend|runner|api|ai-gateway) + 当前仓库
输出: { ok, part, root, missing_paths[], missing_endpoints{}, contract_error, image_endpoint_modules[] }
判定: ok = 必需路径齐全 ∧ 镜像转发面 ⊇ 仓库 RUNNER_ENDPOINTS ∧ 转发面可解析
退出码: 0 / 1（1 = 不得沿用）
```

必需路径表（相对 `/app`，`image_contract.REQUIRED_IMAGE_PATHS`）：

| part | 必需路径 |
|------|---------|
| backend / api | `alembic`、`alembic/versions`、`alembic.ini` |
| runner | 上述三项 + `app/core/execution_dispatch.py` |
| ai-gateway | （无）——网关不承担迁移与 runner 转发面 |

**为什么方向是"镜像 ⊇ 仓库"**：复用镜像上线后，业务调用面由**当前部署配置**决定；
镜像缺任何一个端点，就会在运行期变成 404/500（Batch 248 类事故），因此缺一个即 BLOCK。

## 3. 控制面镜像的 COPY 契约（C249-7）

```
约束: 凡是 app 及其传递依赖（本地模块）必须进镜像
实现: COPY *.py ./        ← 通配，新增模块自动纳入
守护: tests/test_dockerfile_copy_guard.py
      · 从 app.py 出发按 import 图求可达本地模块
      · 用 fnmatch 校验是否被任一 COPY 源匹配
      · 负向用例：换回 Batch 249 的显式列表必须报 migrations.py
```

## 4. 技能回写形态（C249-6）

```
SKILL.md       → 「防冲突规则」新增小节：git diff --stat origin/main...HEAD + 同名文件规模/内容比对
                 「Red Flag（多窗口版）」补一条：未比对 main 就继续旧分支 → 白做一轮
DEPARTMENTS.md → Leader 节第 6 条：接续旧分支前先判断是否已被 main 取代，必要时请 Leader 确认
CHANGELOG.md   → 一条记录（日期 | 批次 | 变更摘要 | 动因），与上述改动同批提交
```
