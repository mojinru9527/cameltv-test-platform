---
name: cameltv-api-test
description: Use when asked to run, write, or debug API/interface tests — "运行接口测试", "执行API测试", "调试接口", "写接口用例", "API回归", "接口自动化". Covers v1 CLI tools (tp api), pytest suites, and GitHub Actions scheduled regression.
---

# CamelTv API 测试

## Overview

执行和编写 CamelTv 项目的 API/接口测试。覆盖测试平台 v1 CLI 工具（`tp api`）、v2 pytest 套件、GitHub Actions 定时回归。

**核心原则：每个接口至少覆盖入参校验、业务逻辑校验、返回值校验三类用例。**

## 何时使用

- 用户说「运行接口测试」「执行 API 回归」「测试这个接口」
- 编写新的接口测试用例
- 调试 API 测试失败
- 查看 API 测试报告

## 测试工具矩阵

| 工具 | 位置 | 用途 | 触发方式 |
|------|------|------|---------|
| `tp api` CLI | test-platform/ | v1 接口测试主命令 | 命令行 / CI |
| pytest + httpx | test-platform-v2/backend/tests/ | v2 后端单元+集成测试 | `pytest` / Jenkins |
| GitHub Actions | .github/workflows/api-regression.yml | 每日 API 回归 | 定时 02:03 UTC |
| GitHub Actions | .github/workflows/prod-smoke-test.yml | 生产冒烟 | 定时 08:07 UTC |
| Playwright API | tests/api-testing/ | API + UI 混合场景 | 手动 / CI |

## 强制工作流程

### 第 1 步：确定测试范围

- 确认目标环境和被测接口。
- 检查是否有现成的测试用例（`tests/api-testing/`、`test-platform-v2/backend/tests/`）。
- 如果是新接口，参考 [tests/test-case-standards/API接口测试方案.md](../../../tests/test-case-standards/API接口测试方案.md) 设计用例。

### 第 2 步：运行已有测试

#### v1 CLI 方式

```bash
cd test-platform
pip install -e .

# 环境健康检查
tp envcheck --env test

# 运行全部 API 测试
tp api run --env test --report data/reports/api-report.xml

# 按标签过滤（smoke / regression / critical）
tp api run --env test --filter smoke

# 运行特定模块
tp api run --env test --module auth
tp api run --env test --module project
```

#### v2 pytest 方式

```bash
cd test-platform-v2/backend
source .venv/bin/activate  # 或 .venv\Scripts\activate

# 运行全部后端测试
python -m pytest tests/ -v --tb=short

# 运行特定测试文件
python -m pytest tests/test_auth.py -v

# 生成 HTML 报告
python -m pytest tests/ -v \
    --html=test-report.html --self-contained-html \
    --junitxml=test-results.xml
```

### 第 3 步：编写新接口用例

按 `tests/test-case-standards/` 规范编写：

**接口用例三要素（必选）：**

1. **入参校验** — 必填参数缺失、类型错误、边界值、特殊字符/SQL注入
2. **业务逻辑校验** — 正常业务流程、权限校验、状态流转、并发冲突
3. **返回值校验** — HTTP 状态码、响应结构（`{code, message, data}`）、字段类型和取值范围

**用例模板：**

```markdown
| 用例编号 | TC-API-{模块}-{编号} |
| 接口名称 | POST /api/v1/{path} |
| 用例标题 | {简短描述测试场景} |
| 前置条件 | {数据准备、认证状态} |
| 测试步骤 | 1. {发送请求的具体参数} 2. {验证点} |
| 预期结果 | HTTP {code}, code={业务码}, data含{字段} |
| 重要程度 | P0 / P1 / P2 |
```

### 第 4 步：分析测试结果

```bash
# v1: 查看报告
cd test-platform
tp report show --file data/reports/api-report.xml

# v2: pytest 输出
# 关注 FAILED、ERROR 标记，查看 traceback

# 查看 Jenkins 报告
# Jenkins → Backend Test Report → 查看失败的 test case
```

### 第 5 步：失败排查

常见接口测试失败原因：

| 现象 | 可能原因 | 排查 |
|------|---------|------|
| 401 Unauthorized | Token 过期或缺失 | 检查 JWT 是否在有效期内，登录接口是否正常 |
| 403 Forbidden | 权限不足 | 检查当前用户角色和资源权限范围 |
| 422 Validation Error | 请求参数不符合 schema | 对照 OpenAPI 文档检查参数格式 |
| 500 Internal Error | 后端异常 | `docker logs cameltv-backend` 查看错误日志 |
| 连接拒绝 | 服务未启动或端口错误 | `curl http://localhost:8000/health` |

## CI 集成

### GitHub Actions（自动）

- **每日 API 回归**：`.github/workflows/api-regression.yml`，每日 02:03 UTC，运行 v1 CLI 全量 API 测试
- **生产冒烟**：`.github/workflows/prod-smoke-test.yml`，每日 08:07 UTC，运行 smoke 标签用例

### Jenkins（自动）

- `Backend: Test` 阶段：PR/push 时运行 v2 pytest 套件
- 报告自动归档到 Jenkins（JUnit XML + HTML）

### 本地手动

```bash
# 模拟 CI 环境
cd test-platform
tp api run --env test --report data/reports/api-ci-test.xml

# 查看摘要
tp report summary --file data/reports/api-ci-test.xml
```

## 测试数据管理

- ⚠️ **不要在测试中硬编码环境相关的 ID**（如项目 ID、用户 ID）。
- ✅ 使用 fixture / setup 在测试前创建所需数据。
- ✅ 测试后清理数据（teardown），避免污染其他测试。
- ✅ 使用独立的测试数据库或数据隔离策略。

## Red Flags — 停下来重做

- 接口用例只有正向测试，缺少参数校验和异常场景 → 覆盖不全
- 预期结果只写「返回成功」无具体验证点 → 不可执行
- 跳过环境健康检查直接跑测试 → 可能误报
- 生产环境测试跑全量用例 → 应该只跑 smoke

## 关联

- [tests/test-case-standards/API接口测试方案.md](../../../tests/test-case-standards/API接口测试方案.md)：接口测试方案标准
- [tests/test-case-standards/接口测试规范.md](../../../tests/test-case-standards/接口测试规范.md)：接口测试编写规范
- [tests/api-testing/](../../../tests/api-testing/)：API 测试用例目录
- [.github/workflows/api-regression.yml](../../../.github/workflows/api-regression.yml)：每日 API 回归 CI
