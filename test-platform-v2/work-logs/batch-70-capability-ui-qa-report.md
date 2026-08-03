# Batch 70 — QA 报告（能力产品化 UI 补齐）

> **QA (🔍)** | Date: 2026-08-03 | Verdict: PASS

## 测试总览

| Slice | 通过 | 失败 | 阻塞 |
|:------|:----:|:----:|:----:|
| 1 API Token 管理 UI | 4+1 E2E | 0 | 0 |
| 2 用例导入导出 UI | 4+1 E2E | 0 | 0 |
| 3 追溯下钻 UI | 1+1 E2E | 0 | 0 |
| 4 报告模板管理 UI | API CRUD + 1 E2E | 0 | 0 |

## 可执行门禁

| # | 门禁 | 命令/方式 | 结果 |
|---|------|-----------|------|
| G1 | 前端 typecheck | `npm run typecheck` | PASS |
| G2 | 前端 build | `npm run build` | PASS（8.3s） |
| G3 | Vitest（api） | `npx vitest run src/api/__tests__` | PASS：11 文件 / 45 用例（含新增 token 4 + import/export 4） |
| G4 | 后端 ruff F821 | `ruff check app/services/trace_service.py --select F821` | PASS |
| G5 | 浏览器 E2E | Playwright（batch-70 8037/5207） | PASS（各 Slice 见下） |

## 逐 Slice 验证

### Slice 1 — API Token 管理
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 系统页 Tab | ✅ | /system 4 个 Tab（用户/角色/审计/API Token），token:list 权限控制 |
| 创建 Token | ✅ | 对话框创建 → 明文一次性展示（复制按钮）+ DB 落库（tpat_ 前缀） |
| 启停/删除 | ✅ | Switch 启停 + 删除二次确认（代码路径，权限 token:manage 控制） |
| 权限 | ✅ | token:list/manage 已存在于权限种子 |

### Slice 2 — 用例导入导出
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 工具栏 | ✅ | testcase 页「导入」「导出 Excel」「导出 XMind」按钮 |
| 导入 | ✅ | xlsx 上传 → toast「导入完成」→ DB 50 条入库 |
| 导出 | ✅ | 下载 test-cases.xlsx（带鉴权头 fetch blob） |

### Slice 3 — 追溯下钻
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 下钻入口 | ✅ | trace 页「追溯下钻」卡片：需求文档选择 → 覆盖明细 → 用例下钻 |
| 用例追溯链 | ✅ | 计划/执行（时间戳+状态）、关联缺陷展示（E2E 通过） |
| 后端补字段 | ✅ | `get_requirement_coverage` cases 补 `id`/`title`（下钻需数字 id） |

### Slice 4 — 报告模板管理
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 入口 | ✅ | 生成报告对话框模板选择旁「管理」按钮 |
| 模板 CRUD（API） | ✅ | POST/GET/PUT/DELETE /report-templates 全 200 |
| 模板 CRUD（UI） | ✅ | 打开管理对话框 → 新建「batch70-ui-模板」→ 列表出现 |

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|:------:|------|------|------|
| B70-Q1 | P3 | 测试期间登录限流（10 次/15 分钟）导致 E2E 误判为按钮缺失 | 429 复现 | ✅ 非缺陷（限流按设计生效），等待窗口后复测通过 |
| B70-Q2 | P3 | 追溯下钻首版传参用 `c.id`，而 coverage cases 缺 `id` 字段 | 下钻空链 | ✅ 已修复（后端补 id/title + 前端用 c.id） |

## 发布建议

状态: **PASS**。四个 API-only 能力已补 UI（C63-1 主体完成）；Playground 前端入口维持 API-only（C22-C2/C3 runner 未验证，文档化）；
回归 45/45 无新增失败。
