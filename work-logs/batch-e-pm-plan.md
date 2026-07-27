# Batch E (Sprint 0.6) — PM 实施计划

> **PM Department (📋)** | Date: 2026-07-02 | Status: Ready for Dev

---

## Sprint 目标

P1 安全基线最终回归测试。在前四批次 (A-D) 已交付 8 项安全修复的基础上，完成三项收尾工作：

1. **C5** — useApi hook 在 React 18 Strict Mode 下的鲁棒性修复
2. **C6** — DataTable + AsyncState 双模式文档化
3. **C7** — 全平台实际 axe-core 无障碍扫描 + 修复
4. **C8** — P1 安全回归测试套件（覆盖批次 A-D 全部修复点）

## 估算

| 条件 | 预估工时 | 复杂度 | 风险 |
|------|---------|--------|------|
| C5 | 1.5h | 中 | 需验证 Strict Mode 双挂载行为 |
| C6 | 1h | 低 | 纯文档，无代码变更 |
| C7 | 2h | 中 | 依赖 axe-core CLI + 浏览器 |
| C8 | 3h | 中高 | 需覆盖 8 个安全维度 |
| **总计** | **7.5h** | | **最终批次，交付即完成 P1 安全基线** |

---

## C5: useApi Strict Mode 双挂载修复

### 问题分析

React 18 Strict Mode 在开发模式下会：
1. 挂载组件 → 运行 effects
2. 卸载组件 → 运行 cleanup
3. 重新挂载组件 → 运行 effects

当前 `useApi.ts` 使用 `didInitialFetch` ref 防止重复 fetch，但第二次挂载时该 ref 已为 `true`，导致不发起请求，页面永远处于 loading 状态。

### 修复方案

**方案 A（推荐）**: 将 `didInitialFetch` 改为在 `useEffect` cleanup 中重置

```typescript
useEffect(() => {
  // ... existing logic
  return () => {
    controllerRef.current?.abort()
    didInitialFetch.current = false  // 允许 Strict Mode 重新挂载时重新 fetch
  }
}, [])
```

**方案 B**: 使用 `useRef` 计数而非 boolean，允许第二次 fetch

选择方案 A，改动最小且语义清晰。

### 影响范围

- `frontend/src/hooks/useApi.ts` — 仅改 cleanup 逻辑
- 验证方式：在 `index.html` 中移除 `<React.StrictMode>` 判断 → 然后恢复 StrictMode，确认所有页面正常加载

### 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/hooks/useApi.ts` | MODIFY | cleanup 中重置 didInitialFetch + 添加 Strict Mode 测试 |

---

## C6: DataTable + AsyncState 集成模式文档

### 背景

批次 D 改造了 12 个页面，使用了两种不同的错误/加载状态管理模式：

**模式 A — AsyncState 包裹（3 个页面）**：
```
workbench, requirement, defect
```
使用 `<AsyncState isLoading={...} isError={...}>` 全包裹

**模式 B — DataTable 内联 ErrorState（7 个页面）**：
```
testplan, report, testcase, project, schedule, trace, system/*
```
使用 `{isError ? <ErrorState/> : <DataTable loading={isLoading}/>}` 三元表达式

### 交付物

文档 `test-platform-v2/docs/async-state-patterns.md`：

1. 两种模式的适用场景
2. 模式选择决策树
3. 代码示例 (copy-paste ready)
4. 迁移指南（从旧模式到新模式）

---

## C7: 全平台无障碍审计

### 审计方法

使用 axe-core CLI 对所有 12 个页面进行扫描：

```bash
# 安装
npm install -g @axe-core/cli

# 扫描每个页面
npx @axe-core/cli http://localhost:5173/workbench
npx @axe-core/cli http://localhost:5173/testcase
# ... 重复 12 个路由
```

### 审计标准

- 目标：**0 critical + 0 serious violations**
- moderate/minor 允许存在，记录到 backlog
- 修复所有 critical 和 serious 问题

### 现已有基础设施（批次 D）

- 全局 focus-visible ring (`globals.css`)
- 色彩对比度 token (`muted-hc`, `border-hc`)  
- skip-to-content 链接 (`MainLayout.tsx`)
- aria-label（SearchInput, Pagination, Sidebar）
- useA11y hook（focus trap + focus restore）
- Lighthouse CI 配置 (`lighthouserc.json`)

### 预期修复

基于批次 D 基础设施，预期仅少量 aria-label 遗漏或 form input 缺少 label 等问题。

---

## C8: P1 安全回归测试套件

### 覆盖矩阵

| # | 安全修复 | 批次 | 测试类型 | 验证点 |
|---|---------|------|---------|--------|
| 1 | JWT httpOnly Cookie | A | 集成测试 | login 设置 cookie; logout 清除; Authorization header deprecated warning |
| 2 | XSS innerHTML 修复 | A | 单元测试 | mindmap fallback 使用 textContent，注入 payload 不执行 |
| 3 | CSRF 中间件 | B | 集成测试 | 无 Origin 的 POST 被拒绝; GET 放行; /api/v1/open bypass |
| 4 | CSP 响应头 | B | 集成测试 | 响应包含 CSP header，值与配置一致 |
| 5 | RBAC 权限补齐 | B | 集成测试 | Token/Notify 路由拒绝无权限用户 |
| 6 | BackgroundTasks 替换 | B | 单元测试 | 确认无裸 create_task 调用 |
| 7 | SMTP TLS 验证 | C | 集成测试 | 证书验证失败抛 SSLError; 证书验证关闭记录 WARNING |
| 8 | 流式上传安全 | C | 集成测试 | 大文件分块; 临时文件隔离 |
| 9 | Security Headers | D | 集成测试 | 5 个 OWASP 响应头全部存在 |
| 10 | 综合场景 | ALL | E2E | 登录→操作→登出 完整链路 |

### 测试文件

```
backend/tests/test_p1_security_regression.py   (~500 lines, ~25 test cases)
```

所有测试使用 `@pytest.mark.integration` 标记，可选择性执行：

```bash
pytest tests/test_p1_security_regression.py -v -m integration
```

---

## 交付流程

```
Product → PM → Design → Dev (4 phases) → QA → Leader
   ✅      ✅       🔜        🔜           🔜      🔜
```

## 分支策略

```
feature/p1-batch-e-security ← develop
```

## 验收标准

- [ ] C5: useApi 在 `<StrictMode>` 下正常工作（无永久 loading）
- [ ] C6: `docs/async-state-patterns.md` 完成（两种模式 + 决策树 + 示例）
- [ ] C7: 12 页面 axe-core 扫描 0 critical + 0 serious
- [ ] C8: 安全回归测试套件 ≥ 20 条，全部通过
- [ ] 全部 4 个 Leader 条件满足
- [ ] Backlog 更新（Sprint 0.6 → 已交付）
