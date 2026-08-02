# Batch 64 — QA 报告（架构解析与仓库拆分基线）

> **QA (🔍)** | Date: 2026-08-02 | Verdict: PASS

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|:------:|:----:|:----:|:----:|
| 10 | 10 | 0 | 0 |

## 变更范围与 CI 分类

- 变更范围：`docs/**`、`scripts/repo-split/**`、`repo-boundaries.json`、`work-logs/**`（Markdown/本地工具类）。
- 按 AGENTS.md §4.2 分类：**Markdown / docs / work-logs / 本地工具 → 前后端重测试跳过**，
  required contexts 返回明确结果；本批不触碰 `test-platform-v2/backend/app/**` 与
  `test-platform-v2/frontend/src/**` 业务代码（`git status` 已验证：仅 2 个文档修改 + 新增文件）。

## 可执行门禁（命令、退出码、结果）

| # | 门禁 | 命令 | 退出码 | 结果 |
|---|------|------|:------:|------|
| G1 | 边界校验器自测 | `py -3.12 scripts/repo-split/validate_repo_boundaries.py --selftest` | 0 | `SELFTEST: PASS (7/7)`：clean / 嵌套覆盖 / 无主文件 / 无主顶层 / 精确重复 / 缺失路径 / schema 错误 |
| G2 | 边界清单真实仓库校验 | `py -3.12 scripts/repo-split/validate_repo_boundaries.py --check` | 0 | `RESULT: PASS` — 1768 个已跟踪路径全覆盖：shared 855 / backend 405 / frontend 361 / deprecated-v1 112 / ops-platform 35 |
| G3 | JSON 合法性 | `py -3.12 -c "json.load(open('repo-boundaries.json'))"` | 0 | valid JSON，UTF-8 正常解析（含 U+2014/U+F022 文件名） |
| G4 | Python 语法 | `py -3.12 -m py_compile scripts/repo-split/validate_repo_boundaries.py` | 0 | 编译通过 |
| G5 | 空白/冲突检查 | `git diff --check` | 0 | 无空白错误 |
| G6 | 密钥泄露扫描 | 正则扫描新增文件（password/token/AKIA/sk-） | 0 命中 | 交付清单仅含环境变量槽位，无明文 Secret |
| G7 | 范围核验 | `git status --short` | 0 | 仅 batch-64 文件；无业务代码改动 |
| G8 | 文档一致性 | 交叉核对验收汇总文档 / prod.yaml / deploy | 0 | 域名、Vercel、Supabase 条目一致 |
| G9 | 历史缺陷检索 | `docs/common-pitfalls.md`、C-CONDITIONS、batch-63 看板 | 0 | 已核对（v1/v2 端口冲突、演示态红线、外部阻塞台账）；无新增冲突 |
| G10 | ruff（F821） | `ruff check`（app 范围） | 跳过 | 本批无 `app/` 代码改动；新脚本 ruff 环境不可用（venv 基础解释器缺失），以 py_compile + 自测 + 代码审查补偿，如实记录 |

## 逐条件验证

### C1: 覆盖矩阵完整性
**变更文件**: `docs/architecture/batch-64-architecture-analysis.md` §4
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 11 件 CLI 工具逐项判定 | ✅ | 5 项已迁移 / 2 项部分 / 4 项缺失（mock/capture/apidiff/datafactory）+2 项部分（logagg/loadtest） |
| server 路由 10 组映射 | ✅ | 主链路已迁移 |
| web-ui 覆盖确认 | ✅ | 与 repo-map 声明一致 |

### C2: 边界机器可校验
**变更文件**: `repo-boundaries.json`、`scripts/repo-split/validate_repo_boundaries.py`
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 100% 已跟踪路径归属 | ✅ | 1768/1768（G2） |
| 最长前缀语义 | ✅ | selftest「nested override」通过 |
| 违规/非法输入非零退出 | ✅ | selftest 4 个负例均按预期退出码 1/2 |

### C3: 生产交付清单
**变更文件**: `docs/production-delivery/生产环境交付清单.md`
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 业务平台生产/测试域名 | ✅ | 6 生产入口 + 6 测试节点映射，与验收汇总文档一致 |
| 测试平台自身基础设施 | ✅ | Vercel 域名 / Supabase ref / Region 一致 |
| 服务器/DB/中间件 | ✅ | 占位项如实标注「待运维回填」，未伪造 |
| 无明文 Secret | ✅ | G6 零命中 |
| production 状态 | ✅ | 保持 `DEFERRED`，未伪造发布证据 |

### C4: 零业务回归
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 后端/前端业务文件改动 | 0 | `git status` 无 `app/`、`src/` 变更 |
| CI 分类 | ✅ | docs/scripts 范围，前后端重测试跳过并记录 |

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|:------:|------|------|------|
| B64-Q1 | P3 | 根目录两个 `pective pipeline — ...` 误提交文件（含尾随 U+F022） | `git ls-files` 根级清单 | 转 C64-2 独立审计删除 |
| B64-Q2 | P3 | 生产 DB/Redis/MQ 地址仍为 `10.x.x.x` 占位 | 交付清单 §3 | 转 C64-3 待运维回填 |
| B64-Q3 | P3 | ruff 环境不可用（venv 基础解释器缺失 `Python312`） | G10 | 记录在案；不阻断（无 app 改动） |

## 发布建议

状态: **READY**（本批交付物范围）　必修复: 0　建议修复: 3（P3，均已转 C64 条件）
