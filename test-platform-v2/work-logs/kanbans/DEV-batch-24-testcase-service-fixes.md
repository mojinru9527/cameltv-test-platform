# Kanban DEV-batch-24-testcase-service-fixes

> **Dev (💻)** | Last updated: 2026-07-20

## 🗺 当前位置
```
Batch 24: 用例服务模块 10 项修复
├── Slice 1: Backend fixes (R.err + sort + domain filter) ✅
├── Slice 2: Frontend fixes (numbered display + filters + delete guard) ✅
├── Slice 3: QA verification 🔄
└── Slice 4: Leader review + PR ⏳
```

## 📋 批次记录

| Batch | 内容 | Slice | 审批 | 耗时 |
|-------|------|-------|------|------|
| 24 | 10 项修复 | 1-2 完成 | Leader 审批中 | ~2h |

## 🔧 Slice 1 — Backend Fixes

### 决策
- **R.err()**：添加 `err()` 类方法到 `R[T]`，使 9 个调用点从 AttributeError 恢复正常
- **排序**：`id.desc()` 替代原三字段排序，新增用例排第一
- **过滤接口测试域**：`list_domain_tree` + `get_category_tree` 双路径过滤

### 实现文件
| 文件 | 变更 |
|------|------|
| `backend/app/schemas/common.py:20-22` | +R.err() classmethod |
| `backend/app/services/test_case_service.py:138` | order_by → id.desc() |
| `backend/app/services/test_case_service.py:224-228` | get_domain_tree 过滤"接口测试" |
| `backend/app/services/test_case_service.py:477-479` | get_category_tree 过滤"接口测试" |

### 验证
- [x] 653 tests passed (pytest)
- [x] R.err() 不再抛 AttributeError
- [ ] 手动验证：POST /domains 返回正确响应

## 🔧 Slice 2 — Frontend Fixes

### 决策
- **步骤渲染**：`formatNumberedText`/`formatStepActions`/`formatStepExpectations` 返回的 `string[]` 改为每元素一个 `<div>`，不再依赖 JSX 隐式 join
- **筛选默认值**：移除 `|| undefined` 转换，让空串 value 能匹配 `SelectItem value=""`；placeholder 显示"全部X"
- **API 防护**：`deleteDomain`/`createModule`/`deleteModule` 加入 `Number.isInteger` 校验，无效 ID 直接 throw（不发请求）
- **搜索按钮**：补充 `refetch()` 调用确保已在第 1 页时也能触发查询

### 实现文件
| 文件 | 变更 |
|------|------|
| `frontend/src/pages/testcase/index.tsx:315` | 搜索按钮 +refetch() |
| `frontend/src/pages/testcase/index.tsx:267-301` | Select placeholder/value 修正 |
| `frontend/src/pages/testcase/index.tsx:406-430` | 步骤信息多行渲染 |
| `frontend/src/api/testcase.ts:39-53` | deleteDomain/createModule/deleteModule ID 校验 |
| `frontend/src/pages/testcase/CategoryManagerDialog.tsx:50-56` | categoryId 支持 null/string |

### 验证
- [x] `categoryId(null)` → null
- [x] `categoryId("1")` → 1 (string→number)
- [x] `categoryId(undefined)` → null
- [ ] 手动验证：表格步骤信息分行显示
- [ ] 手动验证：三个筛选下拉默认显示"全部X"
