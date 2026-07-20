# Batch 24 — QA 报告
> **QA (🔍)** | Date: 2026-07-20 | Verdict: PASS

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 7 | 7 | 0 | 0 |

## 逐条件验证

### C1: R.err() 类方法正常工作
**变更文件**: `backend/app/schemas/common.py:20-22`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| `R.err(code=400, msg="test")` 不抛异常 | ✅ PASS | 返回 `{code:400, msg:"test", data:null}` |
| 9 处调用点全部合法 | ✅ PASS | test_case.py(7) + environment.py(2) |
| 与 `R(code=400, msg=...)` 输出兼容 | ✅ PASS | 两种写法生成相同 JSON |

### C2: 列表排序最新优先
**变更文件**: `backend/app/services/test_case_service.py:138`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| `order_by(TestCase.id.desc())` | ✅ PASS | 最高 ID 排第一 |
| 分页 offset 计算不受影响 | ✅ PASS | `(page-1)*page_size` 仍正确 |

### C3: 接口测试域已隐藏
**变更文件**: `backend/app/services/test_case_service.py:224-228, 477-479`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| `get_domain_tree` 过滤 "接口测试" | ✅ PASS | list comprehension 过滤 |
| `get_category_tree` 过滤 "接口测试" | ✅ PASS | 双路径均已过滤 |
| 域排序仍正确 | ✅ PASS | 只保留用户端/运营后台 |

### C4: 步骤信息分行展示
**变更文件**: `frontend/src/pages/testcase/index.tsx:406-430`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 前置条件每步独立 `<div>` | ✅ PASS | `space-y-0.5`，`max-h-[72px]` 可滚动 |
| 操作步骤每步独立 `<div>` | ✅ PASS | 同上 |
| 预期结果每步独立 `<div>` | ✅ PASS | 同上 |
| 无内容显示 "-" | ✅ PASS | `text-muted-foreground` 样式 |
| `formatNumberedText` 返回 `string[]` | ✅ PASS | 返回已编号字符串数组 |

### C5: 筛选默认值正确
**变更文件**: `frontend/src/pages/testcase/index.tsx:267-301`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 域下拉默认 "全部域" | ✅ PASS | placeholder + SelectItem |
| 模块下拉默认 "全部模块" | ✅ PASS | 同上 |
| 优先级下拉默认 "全部优先级" | ✅ PASS | 同上 |
| 空串 value 可匹配 SelectItem | ✅ PASS | 移除 `\|\| undefined` 转换 |

### C6: API 删除防护
**变更文件**: `frontend/src/api/testcase.ts:39-53`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| `deleteDomain(undefined)` → throw | ✅ PASS | "domainId 无效" |
| `deleteDomain(0)` → throw | ✅ PASS | 同上 |
| `deleteModule(0, 1)` → throw | ✅ PASS | 同上 |
| `createModule(undefined, "x")` → throw | ✅ PASS | 同上 |
| `categoryId` 处理 null/undefined/string | ✅ PASS | 全部返回 null 或正确 int |

### C7: 搜索按钮行为
**变更文件**: `frontend/src/pages/testcase/index.tsx:315`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 第 1 页时点击搜索触发请求 | ✅ PASS | `refetch()` 补充 `setPage(1)` |
| 模糊搜索覆盖所有字段 | ✅ PASS | 后端 ILIKE: title/case_id/api_endpoint/domain/module/preconditions/steps/expected_result |

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| - | - | **无 P0/P1/P2 缺陷** | - | - |
| 1 | P3 | 步骤格式化函数被重复调用（先 `.length` 检查再 `.map()`） | `index.tsx:408-411` — 每行调用 2 次 | 可接受，列表规模小 |
| 2 | P3 | 标签页用例数硬编码（901/795/106） | `index.tsx:219-221` | 预存，非本批次引入 |
| 3 | P3 | `_sanitize_case_data` 原地修改调用者 dict | `test_case_service.py:66-71` | 预存，当前调用方不受影响 |

## 发布建议

**状态: READY** ✅  
必修复: 0  
建议修复: 3 (P3，可下一批次处理)

**发布清单：**
- [x] Backend pytest 全绿 (653 passed)
- [x] `R.err()` 9 调用点全部合法
- [x] 前端 TypeScript 类型检查无新增错误
- [x] API 防护层防御 undefined/null/0/NaN 输入
- [x] 接口测试域已从双路径过滤
- [x] 步骤信息分行渲染符合设计规范
