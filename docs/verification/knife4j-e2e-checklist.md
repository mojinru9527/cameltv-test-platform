# Knife4j/Swagger 导入 E2E 验证清单 (T6)

> 验证目标：确保 OpenAPI/Swagger 文档导入全链路正常工作
> 涉及：URL 导入 + 文本粘贴 + Swagger 2.0/OpenAPI 3.x 兼容

## 1. 前端 UI 验证

| # | 验证项 | 操作 | 预期结果 | 通过 |
|:--:|--------|------|----------|:----:|
| 1.1 | 导入对话框打开 | 进入 API 测试页 → "导入"按钮 | 弹出 ImportDialog，含"URL 导入"/"文本导入"两个 Tab | ☐ |
| 1.2 | 服务名称必填 | 留空服务名点"预览导入" | toast 提示"请输入服务名称" | ☐ |
| 1.3 | URL 导入 Tab | 切换到 URL 导入，输入 URL | 显示 URL 输入框 | ☐ |
| 1.4 | 文本导入 Tab | 切换到文本导入，粘贴 JSON | 显示 Textarea | ☐ |
| 1.5 | 预览结果展示 | 输入有效 URL 后点预览 | 显示版本/总数/新增/已存在 统计 + 接口列表 | ☐ |
| 1.6 | 确认导入 | 预览后点"确认导入并生成用例" | toast "导入完成: N 个接口" → 关闭对话框 | ☐ |
| 1.7 | 导入后刷新 | 导入完成后检查 API 资产列表 | 新 service 出现，包含对应 endpoint | ☐ |

## 2. OpenAPI 3.x 导入

| # | 验证项 | 测试数据 | 验证点 | 通过 |
|:--:|--------|----------|--------|:----:|
| 2.1 | JSON 文本导入 | 粘贴标准 OAS3 JSON | 预览显示正确的接口数 | ☐ |
| 2.2 | YAML 文本导入 | 粘贴 OAS3 YAML | 正确解析（PyYAML） | ☐ |
| 2.3 | requestBody 提取 | OAS3 + requestBody (JSON) | request_schema.body 含 properties | ☐ |
| 2.4 | parameters 提取 | OAS3 + query/path/header params | request_schema.query/path/header 正确 | ☐ |
| 2.5 | response 提取 | OAS3 + 200 response | response_schema 含 status_code + content_type | ☐ |
| 2.6 | 多模块解析 | OAS3 + 多个 tags | 按 tag 分模块 | ☐ |

## 3. Swagger 2.0 导入（关键）

| # | 验证项 | 测试数据 | 验证点 | 通过 |
|:--:|--------|----------|--------|:----:|
| 3.1 | body parameter 提取 | Swagger 2.0 + `in: body` param | request_schema.body 含 schema 内容 ⚠️ **已知 test fail** | ☐ |
| 3.2 | $ref 解析 | Swagger 2.0 + `$ref: '#/definitions/X'` | 正确解析引用 ⚠️ **已知 test fail** | ☐ |
| 3.3 | 基础接口提取 | Swagger 2.0 + GET/POST | method/path/summary 正确 | ☐ |
| 3.4 | definitions 处理 | Swagger 2.0 + definitions | schema 正确解析 | ☐ |

## 4. 服务端验证

| # | 验证项 | 操作 | 验证点 | 通过 |
|:--:|--------|------|--------|:----:|
| 4.1 | ApiService 创建 | 新服务名导入 | api_service 表有新记录 | ☐ |
| 4.2 | ApiEndpoint upsert | 重复导入同一 spec | 已存在接口被更新而非重复插入 | ☐ |
| 4.3 | ImportBatch 记录 | 导入成功后查 DB | import_batch 记录 source_type/source_ref | ☐ |
| 4.4 | source 标记 | Knife4j URL 导入 | endpoint.source = "knife4j_import" | ☐ |
| 4.5 | 自动生成用例 | generate_cases=true | 为每个新 endpoint 生成 test_case | ☐ |
| 4.6 | M1 知识入库 | 导入后查 knowledge_source 表 | 有对应 source_type="api_import" 的记录 | ☐ |

## 5. 错误处理

| # | 验证项 | 操作 | 预期结果 | 通过 |
|:--:|--------|------|----------|:----:|
| 5.1 | 无效 URL | 输入不存在的 URL | toast 错误提示 | ☐ |
| 5.2 | 非 JSON/YAML 响应 | URL 返回 HTML 页面 | 解析失败，友好提示 | ☐ |
| 5.3 | 空 spec | 粘贴空 JSON `{}` | 预览显示 0 个接口或错误 | ☐ |
| 5.4 | 大量接口 | 导入 200+ 接口的 spec | 不超时，正确导入 | ☐ |
| 5.5 | 特殊字符模块名 | tag 含中文/特殊字符 | 正确显示 | ☐ |

## 6. 已知问题

| # | 问题 | 影响 | 状态 |
|:--:|------|------|:----:|
| 6.1 | Swagger 2.0 `in: body` param → request_schema 缺失 | Knife4j Swagger 2.0 body 参数不显示 | 🔴 test fail |
| 6.2 | Swagger 2.0 `$ref` 解析不完整 | definitions 引用解析失败 | 🔴 test fail |
| 6.3 | `test_confirm_creates_batch_with_source_label` 失败 | source 字段可能未正确写入 | 🔴 test fail |

---

## 手动验证步骤（最小可行）

```bash
# 1. 启动后端
cd test-platform-v2/backend
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000

# 2. 启动前端
cd test-platform-v2/frontend
npm run dev

# 3. 浏览器打开 http://localhost:5173
# 4. 登录 (admin / admin123)
# 5. 进入 "API 测试" 页面
# 6. 点击 "导入" 按钮
# 7. 切换到 "文本导入" Tab
# 8. 粘贴以下最小 OAS3 测试数据...
```

## 测试用 OpenAPI 3.0 最小数据

```json
{
  "openapi": "3.0.0",
  "info": {"title": "E2E Test Service", "version": "1.0.0"},
  "paths": {
    "/api/v1/users": {
      "get": {
        "tags": ["users"],
        "summary": "获取用户列表",
        "parameters": [
          {"name": "page", "in": "query", "schema": {"type": "integer"}}
        ],
        "responses": {"200": {"description": "OK"}}
      },
      "post": {
        "tags": ["users"],
        "summary": "创建用户",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "username": {"type": "string"},
                  "email": {"type": "string"}
                },
                "required": ["username"]
              }
            }
          }
        },
        "responses": {"201": {"description": "Created"}}
      }
    }
  }
}
```

## 测试用 Swagger 2.0 最小数据

```json
{
  "swagger": "2.0",
  "info": {"title": "Legacy API", "version": "1.0.0"},
  "paths": {
    "/api/v1/products": {
      "get": {
        "tags": ["products"],
        "summary": "产品列表",
        "parameters": [
          {"name": "category", "in": "query", "type": "string"}
        ],
        "responses": {"200": {"description": "OK"}}
      }
    }
  }
}
```
