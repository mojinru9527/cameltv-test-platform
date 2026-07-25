# Batch 45 — Slice 3 UX 走查与文档

> Date: 2026-07-26 | Status: 完成

---

## C25v2-C2: 固定高度布局验证

### 检查范围
[testcase/index.tsx](test-platform-v2/frontend/src/pages/testcase/index.tsx)
[CaseDrawer.tsx](test-platform-v2/frontend/src/pages/testcase/CaseDrawer.tsx)
[VersionDialog.tsx](test-platform-v2/frontend/src/pages/testcase/VersionDialog.tsx)
[CategoryManagerDialog.tsx](test-platform-v2/frontend/src/pages/testcase/CategoryManagerDialog.tsx)

### 发现

| 位置 | 当前代码 | 评估 |
|------|---------|------|
| index.tsx:288 | `h-[calc(100vh-215px)]` | ✅ 正确使用 calc() + vh 自适应 |
| index.tsx:310 | `style={{ height: 'calc(100vh - 215px)' }}` | ✅ 正确（style prop，同值） |
| index.tsx:406 | `flex-1 min-h-0 overflow-y-auto` | ✅ flex 自适应 + overflow 保护 |
| CaseDrawer.tsx:239 | `max-h-[60vh] overflow-y-auto` | ✅ 合理上限 + overflow |
| CategoryManagerDialog.tsx:280 | `max-h-[42vh] overflow-y-auto` | ✅ 合理 |
| VersionDialog.tsx:63 | `h-[360px] overflow-y-auto` | ⚠️ 固定 360px 高度，Tablet 横屏 (1024×768) 下可用但偏小 |

### 总体评估

**✅ PASS** — 布局使用 `calc(100vh - 215px)` + flex 自适应模式，在 Desktop (1920×1080) 和 Tablet (1024×768) 下均能正确渲染。唯一轻微关注点是 `VersionDialog` 的固定 360px 高度在 Tablet 上偏小，但不影响可用性。

---

## C26KB-C1: 知识中心弹窗 Design 走查

### 检查范围
[knowledge/components/CaptureDialog.tsx](test-platform-v2/frontend/src/pages/knowledge/components/CaptureDialog.tsx)
[knowledge/components/EntityTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/EntityTab.tsx)
[knowledge/components/ArtifactReviewTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/ArtifactReviewTab.tsx)

### 发现

| 组件 | 尺寸设置 | 评估 |
|------|---------|------|
| CaptureDialog | `max-w-lg` (512px) | ✅ 适合截图预览 |
| EntityTab Detail Sheet | `w-full sm:max-w-lg overflow-y-auto` | ✅ 有 overflow 保护 |
| WikiImportDialog | 默认 Dialog size | ⚠️ 未设置 max-h，长表单可能溢出 |

### 总体评估

**✅ PASS (有条件)** — 弹窗整体尺寸合理，有 overflow 保护。`WikiImportDialog` 未设置 `max-h` 是轻微风险，建议后续添加 `max-h-[85vh] overflow-y-auto`。

---

## C26KB-C2: 图谱两域数据隔离

### 检查范围
[GraphTab.tsx:53-67](test-platform-v2/frontend/src/pages/knowledge/components/GraphTab.tsx#L53-L67)

### 发现

数据隔离机制：
1. `domain` state 切换：`'project'`（蓝湖域）↔ `'platform'`（平台域）
2. `loadGraph(domain)` 调用 `fetchGraphView(200, domain)` — domain 作为 API 参数传递
3. UI 切换按钮在 [GraphTab.tsx:291-299](test-platform-v2/frontend/src/pages/knowledge/components/GraphTab.tsx#L291-L299)
4. 每次 domain 切换触发新的 API 调用，完全重新加载数据

### 总体评估

**✅ PASS** — 数据隔离机制正确：domain 切换时发起独立 API 请求，两域数据无交叉污染。前端层面隔离清晰。

---

## batch-18-C7 / C21-P1-5: 迁移双向演练 SOP

参见 [batch-45-staging-migration-drill.md](batch-45-staging-migration-drill.md)

---

## batch-18-C14: 分环境灰度放量 SOP

参见 [batch-45-gradual-rollout-sop.md](batch-45-gradual-rollout-sop.md)
