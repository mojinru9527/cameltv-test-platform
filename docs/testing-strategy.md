---
title: "CamelTv 测试策略总纲"
owner: "qa-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2026-12-26"
tags: ["testing", "strategy", "test-pyramid", "quality"]
related: ["document-standards.md", "common-pitfalls.md", "repo-map.md", "../tests/CLAUDE.md"]
---

# CamelTv 测试策略总纲

> 本文档定义 CamelTv 项目全链路测试的分层策略、工具选型、执行频率和覆盖目标。
> 所有测试活动（用例编写、自动化执行、CI 集成）均应遵循本文档。

---

## 1. 测试金字塔

```
            ╱   E2E   ╲         少量 · 慢 · 脆弱
           ╱  (冒烟)   ╲         Playwright + 手动
          ╱─────────────╲
         ╱  集成/API 测试 ╲      中等 · 快 · 稳定
        ╱  (pytest+httpx)  ╲      v2 pytest + v1 tp api
       ╱───────────────────╲
      ╱     单元测试         ╲    大量 · 极快 · 最稳定
     ╱   (pytest / vitest)   ╲    核心业务逻辑
    ╱─────────────────────────╲
```

| 层级 | 工具 | 覆盖目标 | 执行频率 | 失败即阻塞 |
|------|------|---------|---------|-----------|
| **单元测试** | pytest (BE) + vitest (FE) | 核心 Service 80%+ | 每次 PR | ✅ 是 |
| **集成/API 测试** | pytest + httpx (BE) / tp api (v1 CLI) | 所有公开 API 90%+ | 每次 PR + 每日回归 | ✅ 是 (关键路径) |
| **E2E / 冒烟** | Playwright / 手动 | P0 用户旅程 100% | 每日 + 部署后 | ⚠️ 告警 |

---

## 2. 测试层级详解

### 2.1 单元测试

**范围**：单个函数/方法，不涉及数据库、网络、文件系统。

**后端 (pytest)**：
```
test-platform-v2/backend/tests/
├── test_auth.py          # 认证逻辑
├── test_testcase.py      # 用例 CRUD
└── (待补齐各模块...)
```

**前端 (vitest)**：
```
test-platform-v2/frontend/src/
├── __tests__/            # (待建立)
```

**约定**：
- 文件名：`test_{module}.py` 或 `{module}.test.ts`
- 每个 Service/public 函数至少一个 happy-path 用例
- Mock 外部依赖（数据库、HTTP、文件系统）
- 运行时长 < 5 秒（全量单测）

### 2.2 集成/API 测试

**范围**：接口契约、数据库交互、认证授权流程。

**v2 后端 (pytest + httpx)**：
- 使用 FastAPI `TestClient` + 真实 SQLite 测试数据库
- 覆盖：入参校验 / 业务逻辑 / 返回值结构 / 权限校验
- 参照 [tests/test-case-standards/API接口测试方案.md](../tests/test-case-standards/API接口测试方案.md)

**v1 CLI (tp api)**：
- Playwright 驱动的 API 测试引擎
- 覆盖：v1 工具套件 (Swagger 自动生成 + 手动)
- 参照 [tests/test-case-standards/接口测试规范.md](../tests/test-case-standards/接口测试规范.md)

**接口用例三要素**（每个 endpoint 必须覆盖）：
1. **入参校验**：必填缺失、类型错误、边界值、特殊字符/SQL 注入
2. **业务逻辑**：正常流程、权限校验、状态流转、并发冲突
3. **返回值校验**：HTTP 状态码、响应 envelope (code/message/data)、字段类型

### 2.3 E2E / 冒烟测试

**范围**：完整用户旅程，跨前端→后端→数据库。

**工具**：Playwright (TypeScript) — `tests/automation/ui/`

**UI 自动化模块 (6 个)**：
| 模块 | 覆盖范围 | P0 用例数 |
|------|---------|----------|
| home | 首页推荐 | 待定义 |
| list | 文章列表 | 待定义 |
| detail | 文章详情 | 待定义 |
| pay | 支付流程 | 待定义 |
| refund | 退款流程 | 待定义 |
| bonus | 奖励/Camel Coins | 待定义 |

**生产冒烟 (每日 08:07 UTC)**：
- 健康检查 (`/health`)
- 登录/Token 刷新
- 首页可访问
- 核心 API 可用

### 2.4 专项测试

| 类型 | 工具 | 频率 | 说明 |
|------|------|------|------|
| **音视频质量** | v1 `av_checker` + v2 专项模块 | 版本发布前 | 清晰度/流畅度/延迟 |
| **性能测试** | v1 `load_tester` | 大版本前 | 并发/响应时间 |
| **安全测试** | 手动 + 工具 | 季度 | OWASP Top 10 |

---

## 3. 优先级体系

| 级别 | 含义 | 自动化要求 | 阻塞发布 |
|------|------|-----------|---------|
| **P0** | 核心功能，每版本必测 | 必须自动化 | ✅ 是 |
| **P1** | 常用功能，影响大部分用户 | 优先自动化 | ✅ 是 |
| **P2** | 一般功能 | 时间允许时自动化 | ⚠️ 评审 |
| **P3** | 边缘场景 | 探索性测试为主 | ❌ 否 |

---

## 4. CI/CD 集成策略

```
PR 提交 ──→ GitHub Actions ──→ lint + typecheck + 单元测试 ──→ ✅/❌
                │
push main ──→ Jenkins ──→ 构建镜像 → 单元 → API 回归 → 部署 test → 冒烟
                │
每日 02:03 ──→ GitHub Actions ──→ API 全量回归 (test)
每日 08:07 ──→ GitHub Actions ──→ 生产冒烟 (prod)
```

| 触发条件 | 执行范围 | 系统 | 阻塞条件 |
|----------|---------|------|---------|
| PR 提交 | lint + 单元测试 | GitHub Actions | 任一失败 |
| push main | 构建 + 单元 + API 回归 + 部署 | Jenkins | 单元/构建失败 |
| 每日 02:03 UTC | API 全量回归 (test) | GitHub Actions | 告警 |
| 每日 08:07 UTC | 生产冒烟 | GitHub Actions | 告警 |
| 手动触发 | 部署 staging/prod | Jenkins | 审批 |

---

## 5. 测试数据管理

- ⚠️ **禁止在测试中硬编码环境相关 ID**（项目 ID、用户 ID 等）
- ✅ 使用 fixture/setup 在测试前创建所需数据
- ✅ 测试后清理数据（teardown），避免污染
- ✅ v2 后端测试使用独立 SQLite 数据库（内存或临时文件）
- ✅ 敏感数据（密码、Token）使用环境变量

---

## 6. 测试环境

| 环境 | 用途 | 数据 |
|------|------|------|
| **本地** | 开发自测、新用例调试 | 个人 SQLite / Mock |
| **test** | CI 自动回归、集成测试 | 共享测试库（可重置） |
| **staging** | 预发布验证、E2E | 脱敏生产数据 |
| **prod** | 仅冒烟（只读） | 生产数据 |

---

## 7. 当前覆盖状态与目标

| 模块 | 当前单测 | 当前 API 测试 | 目标单测 | 目标 API |
|------|---------|-------------|---------|---------|
| auth | ✅ 有 | ✅ 有 | 80%+ | 90%+ |
| testcase | ✅ 有 | ✅ 有 | 80%+ | 90%+ |
| testplan | ❌ 无 | ❌ 无 | 80%+ | 90%+ |
| requirement | ❌ 无 | ❌ 无 | 80%+ | 90%+ |
| defect | ❌ 无 | ❌ 无 | 80%+ | 90%+ |
| report | ❌ 无 | ❌ 无 | 80%+ | 90%+ |
| schedule | ❌ 无 | ❌ 无 | 80%+ | 90%+ |
| project | ❌ 无 | ❌ 无 | 70%+ | 80%+ |
| system | ❌ 无 | ❌ 无 | 70%+ | 80%+ |
| dashboard | ❌ 无 | ❌ 无 | 70%+ | 80%+ |
| trace | ❌ 无 | ❌ 无 | 70%+ | 80%+ |
| notify | ❌ 无 | ❌ 无 | 70%+ | 80%+ |
| av_check | ❌ 无 | ❌ 无 | 演示态 | 演示态 |
| ui_test | ❌ 无 | ❌ 无 | 演示态 | 演示态 |

> 注：av_check 和 ui_test 为演示态模块，暂不要求完整测试覆盖。

---

## 8. 关联文档

- 测试标准：[tests/test-case-standards/](../tests/test-case-standards/)
- 测试资产：[tests/CLAUDE.md](../tests/CLAUDE.md)
- v2 测试基础设施：G4 切片 (见 [test-platform-v2/docs/改进任务backlog.md](../test-platform-v2/docs/改进任务backlog.md))
- CI/CD：[deploy/CLAUDE.md](../deploy/CLAUDE.md)
- API 测试方案：[tests/test-case-standards/API接口测试方案.md](../tests/test-case-standards/API接口测试方案.md)
