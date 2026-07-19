# Batch 20 — QA 报告
> **QA (🔍)** | Date: 2026-07-20 | Verdict: PASS (1 pre-existing failure unrelated)

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 12 | 11 | 1 (pre-existing) | 0 |

## 逐条件验证

### C1: 后端 Model — TestCase is_deleted 字段
**变更文件**: `backend/app/models/test_case.py:48`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| is_deleted mapped_column 声明 | ✅ PASS | `Mapped[bool] = mapped_column(default=False, index=True)` |
| 与 DB 列一致 | ✅ PASS | 迁移 20260715 已建列，模型对齐 |

### C2: 后端 Service — list_cases 过滤 is_deleted
**变更文件**: `backend/app/services/test_case_service.py:93-94`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| stmt 含 is_deleted == False | ✅ PASS | `TestCase.is_deleted == False` |
| count_stmt 同步过滤 | ✅ PASS | 计数语句同步 |

### C3: 后端 Service — delete/batch_delete 软删除
**变更文件**: `backend/app/services/test_case_service.py:171-189`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| delete_case 设 is_deleted=True | ✅ PASS | `row.is_deleted = True; db.flush()` |
| batch_delete 批量设标记 | ✅ PASS | `r.is_deleted = True` |
| 不再 db.delete(row) | ✅ PASS | 硬删除已移除 |

### C4: 后端 Service — get_domain_tree 过滤
**变更文件**: `backend/app/services/test_case_service.py:194-216`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 查询过滤 is_deleted=False | ✅ PASS | `TestCase.is_deleted == False` |
| _domain_order 移除"接口测试" | ✅ PASS | 仅保留 `{"用户端": 0, "运营后台": 1}` |

### C5: 后端 API — 分类 CRUD 端点
**变更文件**: `backend/app/api/v1/test_case.py:50-148`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| POST /domains | ✅ PASS | 创建域 + 重名检查 |
| PUT /domains/{id} | ✅ PASS | 更新域名称 |
| DELETE /domains/{id} | ✅ PASS | 级联逻辑删除模块+用例 |
| POST /modules | ✅ PASS | 创建模块 + 域存在检查 |
| PUT /modules/{id} | ✅ PASS | 更新模块名 |
| DELETE /modules/{id} | ✅ PASS | 级联逻辑删除关联用例 |
| 静态路径先于动态 | ✅ PASS | /domains /modules 在 /{case_id} 之前 |

### C6: 前端 — CaseDrawer 移除 api_spec_ref
**变更文件**: `frontend/src/pages/testcase/CaseDrawer.tsx`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| Zod schema 无 api_spec_ref | ✅ PASS | 已删除 line 46 |
| 表单无"关联引用" label+Input | ✅ PASS | 已删除 lines 478-482 |
| TS 编译无错误 | ✅ PASS | CategoryManager/CaseDrawer 0 error |

### C7: 前端 — 优先级独立列
**变更文件**: `frontend/src/pages/testcase/index.tsx`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 表头含"优先级"列 | ✅ PASS | `w-[72px]` 插入 checkbox 和编号之间 |
| Badge 在独立 TableCell | ✅ PASS | 从标题 cell 移出到独立列 |
| 标题 cell 不含 Badge | ✅ PASS | 仅剩 API 类型 Badge + 标题文本 |

### C8: 前端 — apitest 默认 Tab + DebugTab 接线
**变更文件**: `frontend/src/pages/apitest/index.tsx`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 默认 Tab = 'assets' | ✅ PASS | `useState('assets')` |
| DebugTab 收到 endpoint prop | ✅ PASS | `<DebugTab endpoint={debugEndpoint} />` |

### C9: 后端 apitest 搜索扩展 + 前端路径显示
**变更文件**: `backend/app/api/v1/apitest.py:252-257`, `frontend/src/pages/apitest/components/AssetTab.tsx:216`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 搜索含 ApiEndpoint.module | ✅ PASS | `ApiEndpoint.module.ilike(like)` |
| 搜索含 ApiService.name | ✅ PASS | `ApiService.name.ilike(like)` |
| 路径 /→- 显示转换 | ✅ PASS | `ep.path.replace(/\//g, '-')` |

### C10: DebugTab 默认环境"测试5"
**变更文件**: `frontend/src/pages/apitest/components/DebugTab.tsx:95-105`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 自动查找 name='测试5' | ✅ PASS | `data.find((e) => e.name === '测试5')` |
| 自动设 envId + baseUrl | ✅ PASS | `setEnvId(test5.id); setBaseUrl(test5.base_url)` |

### C11: ApiEndpoint remark 全链路
**变更文件**: 5 个文件
| 检查项 | 结果 | 说明 |
|--------|------|------|
| Model 有 remark 列 | ✅ PASS | `api_asset.py` |
| Schema Create/Update/Out | ✅ PASS | `api_asset.py` schemas |
| Frontend Type 有 remark | ✅ PASS | `types/index.ts` |
| AssetTab 展示备注 | ✅ PASS | `📝 {ep.remark}` |
| Alembic 迁移 | ✅ PASS | `20260720_api_endpoint_remark.py` |

### C12: 前端 API — 分类 CRUD 函数
**变更文件**: `frontend/src/api/testcase.ts`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| createDomain/updateDomain/deleteDomain | ✅ PASS | 3 个函数 |
| createModule/updateModule/deleteModule | ✅ PASS | 3 个函数 |
| TestCaseDomainCategory 类型 | ✅ PASS | 已导出 |
| TestCaseModuleCategory 类型 | ✅ PASS | 已导出 |

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 1 | P3 (pre-existing) | test_openvpn_service: Settings 缺少 openvpn_auto_connect_enabled 属性 | 后端 pytest 1 fail | 已记录，非本 batch |

## 测试执行结果

- **后端 pytest**: 399 passed, 1 failed (pre-existing VPN test), 5 warnings
- **前端 tsc --noEmit**: 0 errors (our changed files), 6 pre-existing errors in unrelated files (TriagePanel, ReviewPage)
- **commit**: 2 commits pushed to `feature/batch-20-fix-seven-gaps`

## 发布建议

**状态**: READY ✅
- 必修复: 0（本 batch 引入）
- 已记录: 1（pre-existing VPN test）
- 建议修复: 0
