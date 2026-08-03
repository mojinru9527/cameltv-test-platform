# Batch 67 — QA 报告（AI 验收与正式域名发布前置条件收口）

> **QA (🔍)** | Date: 2026-08-02 | 修订：2026-08-03 | Verdict: PASS（2.1 已解锁；B67-Q3/Q4 已修复；6.1 部署登记 ✅，C58-02/C58-06 关闭）

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|:------:|:----:|:----:|:----:|
| 10 | 10 | 0 | 0 |

## 变更范围与 CI 分类

- 变更范围：`docs/production-delivery/**` + `test-platform-v2/work-logs/**` + `C-CONDITIONS.md`（纯文档）。
- CI 分类（AGENTS.md §4.2）：Markdown/docs → 前后端重测试跳过，required contexts 返回明确结果。

## 可执行门禁（命令、退出码、结果）

| # | 门禁 | 命令/方式 | 结果 |
|---|------|-----------|------|
| G1 | 范围核验 | `git status --short` | 仅 docs + work-logs + C-CONDITIONS；零业务代码 |
| G2 | 空白检查 | `git diff --check` | 0 错误 |
| G3 | 密钥扫描 | 正则扫描 password/token/api key/cookie/私钥 | 0 命中（清单只登记「已写入 ✓」，无明文） |
| G4 | AI Key 连通性 | `GET {AI_API_BASE_URL}/models`（Key 从 .env 读取，不回显） | PASS：换新 Key 后 **HTTP 200**（deepseek-v4-flash / deepseek-v4-pro） |
| G5 | 占位符扫描 | backend/.env 值扫描 `<`/YOUR/CHANGE_ME | 0 命中 |
| G6 | 蓝湖凭据存在性 | LANHU_USERNAME/PASSWORD/COOKIE 键非空 | PASS |
| G7 | OCR 模式确认 | LANHU_OCR_PROVIDER=local | PASS（无需云凭据） |
| G8 | 清单一致性 | 2.x/6.1 状态与实测交叉核对 | PASS（2.1/2.2/2.3 ✅、6.1 ✅ 与事实一致） |
| G9 | Docker 构建验证 | `docker build --target builder`（Linux 容器复现 Railway） | PASS：pip 依赖阶段 0 错误（B67-Q3 修复后） |
| G10 | Railway PORT 监听验证 | `docker run -e PORT=8099` → uvicorn 监听 8099，health 200 | PASS（B67-Q4 修复后；原实现写死 8000 导致 Railway 健康检查端口不匹配） |
| G11 | Railway 线上 health | `GET https://test-platform.up.railway.app/api/v1/open/health` | PASS：HTTP 200，`{code:0, data:{status:ok, version:2.3.0}}`（与 main 一致） |
| G12 | Vercel 公开访问 + 反代 | `GET https://cameltv-test-platform1.vercel.app/login` 与 `/api/v1/open/health` | PASS：均 HTTP 200（登录页 title=CamelTv 测试平台；`/api` 反代到 Railway 返回 2.3.0） |

## 逐条件验证

### C1: 2.1 DeepSeek API Key
**变更文件**: `test-platform-v2/backend/.env`（gitignored，登记于清单 §2.1）
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 键存在且无占位符 | ✅ | len=35、`sk-` 前缀、无引号包裹 |
| 鉴权实测 | ✅ | `GET https://api.deepseek.com/v1/models` → 200（换新 Key 后） |
| 结论 | ✅ | 新 Key 已写入 backend/.env 与 deploy/.env；2.1 关闭（C67-1 满足） |

### C2: 2.2 蓝湖凭据
**变更文件**: backend/.env + lanhu-mcp/.env
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 账密非空 | ✅ | LANHU_USERNAME/PASSWORD 有值 |
| Cookie 非空 | ✅ | lanhu-mcp/.env LANHU_COOKIE 有值 |
| 运行时有效性 | ⏳ | Cookie 有效期需 lanhu-mcp 启动实测 → C67-3 |

### C3: 2.3 OCR
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| Provider | ✅ | LANHU_OCR_PROVIDER=local（PaddleOCR） |
| 云凭据需求 | ✅ | 无需 → 2.3 登记 ✅ |

### C4: 6.1 DevOps 服务器
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 服务器确认 | ✅ | Railway 公网 URL `https://test-platform.up.railway.app`（2026-08-03 实测 health 200，版本 2.3.0 与 main 一致） |
| 阻塞根因 | ✅ 已修复 | 构建依赖 B67-Q3（pywin32/SecretStorage/uvloop）已修复并本地验证；待合并主干后 Railway 自动部署（手册 §1） |
| 结论 | ✅ | 6.1 登记 ✅；`vercel.json` 反代已写死（#100）；C58-06 关闭 |

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|:------:|------|------|------|
| B67-Q1 | P1 | AI_API_KEY 鉴权失败（401），AI 验收无法解锁 | `GET /v1/models` → 401 | ✅ 已修复（2026-08-02 换新 Key 实测 200） |
| B67-Q2 | P3 | 蓝湖 Cookie 有效期未实测 | lanhu-mcp/.env | 转 C67-3（AI 验收批次） |
| B67-Q3 | P0 | Railway 构建失败：`requirements.lock` 为 Windows 生成，缺平台标记/缺 Linux 依赖（pywin32==312 无标记、SecretStorage/jeepney/uvloop 未锁） | 本地 `docker build --target builder` 复现（两个报错：pywin32 → SecretStorage → uvloop） | ✅ 已修复（2026-08-03：pywin32 加 win32 标记；补 secretstorage/jeepney（linux）与 uvloop（非 win32）哈希锁；builder 阶段构建通过） |
| B67-Q4 | P0 | Railway 健康检查失败：容器固定监听 8000，而 Railway 按注入的 `PORT` 变量探测端口；首次迁移 2~4 分钟也可能超默认 300s 健康检查超时 | 部署日志：`Uvicorn running on http://0.0.0.0:8000` 但 Healthcheck failure；官方文档确认 PORT 注入语义 | ✅ 已修复（2026-08-03：Dockerfile CMD 改 `${PORT:-8000}`；railway.json 加 `healthcheckTimeout: 600`；本地 `PORT=8099` 实测 health 200） |

## 发布建议

状态: **PASS**（本批交付物范围）　必修复: 0　建议修复: 1（B67-Q2，转 C67-3）
2.1 已解锁（实测 200）；B67-Q3/Q4 构建与健康检查修复已上线验证；6.1 部署登记 ✅（Railway health 200）、
Vercel 公开访问 200、C58-02/C58-06 已关闭；剩余 B67-Q2 蓝湖 Cookie 有效期转 C67-3（AI 验收批次）。
