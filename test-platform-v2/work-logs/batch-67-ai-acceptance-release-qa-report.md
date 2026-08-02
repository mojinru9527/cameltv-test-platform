# Batch 67 — QA 报告（AI 验收与正式域名发布前置条件收口）

> **QA (🔍)** | Date: 2026-08-02 | Verdict: PASS（2.1 已解锁；6.1 仍为外部待办）

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|:------:|:----:|:----:|:----:|
| 8 | 7 | 0 | 1 |

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
| G8 | 清单一致性 | 2.x/6.1 状态与实测交叉核对 | PASS（2.1 ⏳、2.2/2.3 ✅、6.1 ⏳ 与事实一致） |

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
| 服务器确认 | ❌ | 未提供 Railway URL / 服务器地址 |
| 阻塞根因 | 记录 | Dockerfile 子模块修复已合入；重试部署待用户操作（手册 §1） |
| 结论 | ⏳ | 登记为待提供；C58-06 维持 OPEN |

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|:------:|------|------|------|
| B67-Q1 | P1 | AI_API_KEY 鉴权失败（401），AI 验收无法解锁 | `GET /v1/models` → 401 | ✅ 已修复（2026-08-02 换新 Key 实测 200） |
| B67-Q2 | P3 | 蓝湖 Cookie 有效期未实测 | lanhu-mcp/.env | 转 C67-3（AI 验收批次） |

## 发布建议

状态: **PASS**（本批交付物范围）　必修复: 0　建议修复: 1（B67-Q2，转 C67-3）
2.1 已解锁（实测 200）；6.1 仍为外部待办（用户提供服务器 URL 后关闭），不构成本批交付缺陷。
