# Batch 259 — Design Spec

> **Design (🎨)** | Date: 2026-09-18 | Status: 就绪

## 0. 技术体系确认

后端 FastAPI + SQLAlchemy 2.0 + Alembic；前端 shadcn/ui + Radix + Tailwind（B2-6）。
本批以**执行/落盘边界**为主，UI 面只有 B2-6 一处。

## 1. 模块与接口规格表

### 1.1 `app/core/spec_guard.py`（新增，B2-2）

| 符号 | 契约 |
|------|------|
| `DANGEROUS_PATTERNS` | `(规则名, 正则, 说明)` 三元组清单，覆盖 `child_process`、`execSync`/`spawnSync`、`fs.writeFile*`/`fs.appendFile*`/`createWriteStream`、`require('net')`/`tls`/`http.request` 直连、`process.env` 读取 |
| `assert_spec_safe(code) -> list[str]` | 命中即返回可读原因列表（含 1-based 行号与规则名）；无命中返回 `[]`。**纯函数，不做 I/O**，便于在三条执行路径复用 |
| `SpecNotAllowedError(ValueError)` | 调用方把原因转成用户可读错误时使用 |

**关键决策**：`assert_spec_safe` 只**报告**，不抛异常；由调用方决定如何拒绝（三条路径的错误文案不同）。
这样它既能用于"拦执行"，也能用于"生成后立刻提示"，不会因为一处调用策略不同而分裂成两份实现。

**边界声明（写进模块 docstring）**：静态拦截只能拦"明显的"危险 API，**不是沙箱**；
真正的隔离靠 `execution_sandbox`（环境/资源/文件/网络）。两者缺一不可，不能互相替代。

### 1.2 `app/integrations/object_storage/local.py`（B2-4）

| 方法 | 变更后契约 |
|------|-----------|
| `_path(uri)` | `base = Path(base_dir).resolve()`；`target = (base / rel).resolve()`；`target.is_relative_to(base)` 不成立 → `StorageError("对象路径越权")`；拒绝空 URI 与绝对路径 |
| `put/get/exists/delete` | 统一走 `_path`，不各自拼路径 |

写法锚点：与 `app/api/v1/lanhu_evidence_assets.py:86` 的 `is_relative_to` 保持一致（同仓只留一种收敛写法）。

### 1.3 密钥派生（B2-5）

| 位置 | 变更 |
|------|------|
| `app/core/cipher.py` | 保持唯一派生实现（`effective_secret_key` → sha256 → urlsafe_b64 → Fernet） |
| `app/services/ai_config_service.py` | 删除本地 `_fernet()`，改为 `from app.core.cipher import encrypt_value, decrypt_value`（保留函数名以免调用点漂移） |
| `app/main.py`（启动） | `assert_cipher_key_consistency()`：无 `SECRET_KEY`（即走自动生成）+ 库中已有密文 → fail-fast，错误文案说明"存量密文将无法解密，请配置 SECRET_KEY 或先清理" |

### 1.4 `execution_sandbox`（B2-1，H1）

| 维度 | 现状 | 本批补齐 |
|------|------|---------|
| 环境变量 | ✅ 白名单 + `CAMELTV_*` 前缀 | — |
| 资源上限 | ✅ POSIX rlimit | — |
| 文件写入 | ❌ | 执行工作区限定在临时目录；`EXECUTION_WORKSPACE_ROOT` 之外的**持久卷**写入必须失败 |
| 出网 | ❌ | 白名单（被测系统域名 + 平台 API 域名）；非白名单目标必须失败 |
| 平台 secret/DB 口令 | ✅ 不在白名单内 | 补回归用例证明读 `.env`/读 `SECRET_KEY` 拿不到 |

## 2. 状态设计核对（四态，B2-6 菜单）

| 状态 | 触发 | 呈现 |
|------|------|------|
| Loading | 用户/权限加载中 | 骨架，不闪烁出 8 个入口再收敛到 4 个 |
| Empty | 无任何可见入口（权限极小） | 明确文案 + 至少保留「我的待办」 |
| Error | 权限拉取失败 | 可重试，不静默降级成"全部可见" |
| 正常 | tester | ≤4 一级入口 + 1 个专家区入口 |

## 3. 设计 QA 走查发现（P0–P3，附文件:行号）

### 🔴 P1-1 对象存储无路径收敛
`app/integrations/object_storage/local.py:24-26`：`normpath(join(base_dir, rel))` 不阻止 `..` 逃逸。
→ **建议**：`resolve` + `is_relative_to`（§1.2）。

### 🔴 P1-2 密钥两套派生
`app/core/cipher.py:26` 用 `effective_secret_key`，`app/services/ai_config_service.py:61-62` 用 `secret_key`。
→ **建议**：统一到 `cipher.py` + 启动 fail-fast（§1.3）。

### 🔴 P1-3 把 dry-run 当沙箱（表述性但会误导架构决策）
`app/services/case_compiler_service.py:6` 写「生成后 sandbox 校验: npx playwright test --dry-run」。
dry-run 仍执行 spec 顶层语句，**不是安全边界**。
→ **建议**：改为「语法检查」，并补静态拦截（B2-2）。

### 🟠 P2-1 计划执行路径跳过校验
`app/services/test_plan_service.py:612` 显式 `validate=False`。
→ **建议**：去掉该实参，走默认 `validate=True`。

### 🟠 P2-2 H1 的"无持久卷写 / 无内网 egress"目前只是文字
`app/core/execution_sandbox.py` 只有环境与 rlimit；三个 H1 硬线中的两个尚未落地。
→ **建议**：§1.4；且"沙箱"这个词必须有回归用例兜住（bug-guard 规则 4：文档承诺=可执行校验）。

### 🟡 P3-1 一级导航项数量无校验
`frontend/src/layouts/nav-config.ts` 无"≤4"断言，02 白名单承诺无法执行校验。
→ **建议**：B2-6 补 E2E/单测断言。

## 4. 设计签核

结论：**通过**（P1-1/P1-2/P1-3 即本批 Task 1–3；P2-1/P2-2/P3-1 已纳入本批）。
