# Batch 46 — Remaining C-Conditions — Design Spec

> **Design (🎨)** | Date: 2026-07-26 | Status: 就绪

## 0. 技术体系确认

shadcn/ui + Radix + Tailwind + CVA；Token 走语义类（bg-muted / text-muted-foreground / border / variant）。
**大部分任务为修复/验收，无新 UI 组件。仅 C45-C3 API 和 C45-C4 样式修正涉及设计。**

## 1. C45-C4: WikiImportDialog 样式修正

### 组件规格

| 属性 | 值 |
|------|-----|
| 组件 | Dialog (shadcn/ui) |
| max-height | `max-h-[85vh]` |
| overflow | `overflow-y-auto` |
| 位置 | DialogContent 内部滚动区 |

### 改动

在 WikiImportDialog 的 DialogContent 或内部 wrapper 添加 Tailwind class：`max-h-[85vh] overflow-y-auto`。

### 设计 QA

无需额外走查——这是已有的 P3 设计债务，直接应用 batch-45 Leader 指定的 class。

## 2. C45-C3: Playground Compile/Execute API

### API 设计

```
POST /api/v1/playground/compile
Content-Type: application/json

Request:
{
  "source": "string",        // 功能用例 Markdown/Gherkin 文本
  "source_type": "gherkin"   // gherkin | markdown | plain
}

Response 200:
{
  "spec_code": "string",     // 生成的 .spec.ts 代码
  "spec_type": "playwright", // 目标框架
  "compile_ms": 123          // 编译耗时 ms
}

Response 422:
{
  "detail": "Compilation failed: {reason}"
}
```

```
POST /api/v1/playground/execute
Content-Type: application/json

Request:
{
  "spec_code": "string",     // .spec.ts 代码
  "timeout_ms": 30000        // 执行超时（可选，默认 30000）
}

Response 200:
{
  "passed": true,
  "screenshot_base64": "...", // 截图
  "stdout": "...",
  "stderr": "...",
  "duration_ms": 4567
}
```

### 编译策略

Phase 1 采用模板拼接：从 Gherkin Given/When/Then 生成 Playwright `test()` 块。

```
Gherkin:                       →  .spec.ts:
Given I am on "/login"         →  await page.goto('/login');
When I click "#submit"         →  await page.click('#submit');
Then I should see "Welcome"    →  await expect(page.locator('body')).toContainText('Welcome');
```

正则匹配 Gherkin 关键字 → 映射到 Playwright API → 拼接完整 test 文件。

### 路由注册

在 `test-platform-v2/backend/app/api/v1/__init__.py` 或 `main.py` 注册 `playground` router，prefix `/api/v1/playground`。

## 3. 非设计项（无需规范）

- C45-C1/TPv2-B19-C2: 前端 CI/测试修复，无视觉变更
- C43-1/C43-2/C44-C1/C44-C4/C45-C2: Docker/staging 操作验收，无代码变更

## 4. 设计签核

结论：通过。仅有的两个设计项（API 接口 + 单 class 样式修正）规格明确，可直接开发。
