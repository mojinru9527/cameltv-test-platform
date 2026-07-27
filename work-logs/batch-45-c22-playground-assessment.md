# C22 Playground 可行性评估

> C22-C2 + C22-C3: 端到端编译链路 + 统一编排器批量执行
> 评估日期: 2026-07-26

---

## 1. 现有资产

### 编译侧 (case_compiler_service.py)

| 能力 | 状态 | 说明 |
|------|:----:|------|
| `compile_to_playwright()` | ✅ 已有 | 接受 TestCase ORM 对象，生成 .spec.ts |
| LLM 调用 | ✅ | DeepSeek，含系统提示词模板 |
| 代码清理 | ✅ | 去除 markdown fence、`tsc --noEmit` 验证 |
| 单元测试 | ✅ | `test_case_compiler.py` (mocked LLM) |

### 执行侧 (playwright_executor.py)

| 能力 | 状态 | 说明 |
|------|:----:|------|
| `run_playwright_test()` | ✅ 已有 | subprocess 执行 .spec.ts/.spec.js |
| 取消轮询 | ✅ | 每 2s 检查取消标记 |
| 超时控制 | ✅ | 可配超时 |
| 结果解析 | ✅ | JSON report → assertion results |
| 截图采集 | ✅ | 自动保存截图到 artifacts |

### 缺失

| 能力 | 状态 | 说明 |
|------|:----:|------|
| **API 端点** | ❌ 缺失 | `compile_to_playwright` 无 API 路由 |
| **编排器** | ❌ 缺失 | 无服务连接编译→执行→报告全链路 |
| **前端页面** | ❌ 缺失 | 无 Playground 可视化界面 |
| **错误恢复** | ❌ 缺失 | 编译失败后的重试/回退机制 |

---

## 2. 实现路径

### Phase 1: 最小可行链路 (C22-C2)
```
TestCase → compile_to_playwright() → .spec.ts file → playwright_executor → result
```

**所需工作**:
1. 新增 API 端点: `POST /api/v1/playground/compile` + `POST /api/v1/playground/execute`
2. 新建 Playground 服务: 连接 compiler + executor
3. 新建前端页面: Playground 表单 + 结果展示

**预估工作量**: 4-6h (后端 2h + 前端 2h + 测试 2h)

### Phase 2: 批量编排 (C22-C3)
```
[3 API + 3 功能] → orchestrator → 6/6 results → auto report
```

**所需工作**:
1. 新建 Orchestrator 服务: 并发执行 + 进度追踪 + 结果聚合
2. 扩展 API: `POST /api/v1/playground/batch`
3. 自动报告生成

**预估工作量**: 3-4h (后端 2h + 测试 1h + 文档 1h)

---

## 3. 风险

| 风险 | 严重级 | 缓解措施 |
|------|:------:|---------|
| LLM 编译质量不稳定 | P1 | 增加 `tsc --noEmit` 验证，失败重试(最多 3 次) |
| 编译耗时过长 | P2 | 设置 30s 超时，后台异步执行 |
| 生成的 .spec.ts 有安全风险 | P2 | 沙箱执行（已有 subprocess 隔离） |
| 前端 Playground SSE 连接 | P2 | 优先轮询模式 |

---

## 4. 建议

**✅ 可行** — 现有编译器和执行器基础设施足够支撑 C22-C2 最小链路。建议在 batch-46+ 中实施 Phase 1，作为独立 feature branch。

**优先级**: P1 (已具备核心技术能力，缺的是 API 粘合层和前端界面)
