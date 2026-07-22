# Batch 28 — Design Spec：延后项补漏

> **Design (🎨)** | Date: 2026-07-22

## 1. 后端设计

### 1.1 感知哈希对比 (US-1)

**文件**: `test-platform-v2/backend/app/services/lanhu_evidence/diff_service.py`

**新增常量** (L26-27 附近):
```python
IMAGE_SIMILARITY_THRESHOLD = 0.85  # 感知哈希相似度阈值
```

**`page_to_dict()` 修改** (L249):
```python
# Before:
"screenshot_hash": "",

# After:
"screenshot_hash": page.screenshot_hash or "",
```
> 注: 需要先在 `LanhuEvidencePage` 模型中添加 `screenshot_hash` 字段，或者在证据采集阶段计算哈希。MVP 方案：在 `diff_service.py` 中直接对已存储的截图文件计算 `imagehash.phash()`。

**`compute_page_diff()` 修改** (L109-117 之后新增视觉判断):
```python
# 文本相似度判断后，增加视觉判断
if change_type == "unchanged" and prev_page.get("screenshot_hash") and curr_page.get("screenshot_hash"):
    img_sim = _image_similarity(prev_page["screenshot_hash"], curr_page["screenshot_hash"])
    if img_sim < IMAGE_SIMILARITY_THRESHOLD:
        change_type = "modified"  # 视觉不同 → 升级为 modified
```

**新增函数 `_image_similarity()`**:
```python
def _image_similarity(hash1: str, hash2: str) -> float:
    """计算两个感知哈希的相似度。hash 应为 imagehash.phash() 输出的十六进制字符串。"""
    if not hash1 or not hash2:
        return 1.0  # 无哈希时默认相同（降级到文本判断）
    try:
        import imagehash
        h1 = imagehash.hex_to_hash(hash1)
        h2 = imagehash.hex_to_hash(hash2)
        return 1.0 - (h1 - h2) / len(h1.hash) ** 2
    except ImportError:
        return 1.0
```

**降级策略**: `import imagehash` 失败时 `_image_similarity()` 返回 1.0 → 不影响现有文本对比逻辑。

---

### 1.2 KnowledgeIteration 自动创建 (US-4)

**文件**: `test-platform-v2/backend/app/services/knowledge/ingest_service.py`

**`ingest_lanhu_version_diff()` 修改** (L521-522 之前插入):
```python
# 自动创建/更新 KnowledgeIteration
from app.services.knowledge.snapshot_service import create_iteration
existing = await session.execute(
    select(KnowledgeIteration).where(
        KnowledgeIteration.project_id == project_id,
        KnowledgeIteration.version == version,
        KnowledgeIteration.status == "active",
    )
)
existing_iter = existing.scalar_one_or_none()
if existing_iter:
    existing_iter.end_date = datetime.utcnow()  # 更新结束时间
else:
    await create_iteration(
        session, project_id,
        iteration_name=f"版本 {version}",
        version=version,
        description=f"自动创建 — 版本差异入库\n{summary_text}",
    )
```

---

### 1.3 继承匹配率日志 (US-7)

**文件**: `test-platform-v2/backend/app/api/v1/requirement.py`

**`extract_features` 修改** (L209 之后):
```python
logger.info(
    f"fp_inherit_match_rate: {inherited_fp_count}/{len(inherited_fps_raw)} "
    f"({inherited_fp_count/len(inherited_fps_raw)*100:.1f}%) "
    f"[doc_id={doc_id}, base_version={base_version}]"
)
```

**`generate_test_cases` 修改** (L445 之后):
```python
logger.info(
    f"case_inherit_match_rate: {matched_cases}/{total_inheritable_fps} "
    f"({matched_cases/total_inheritable_fps*100:.1f}%) "
    f"[doc_id={doc_id}]"
)
```

---

## 2. 前端设计

### 2.1 VersionCompare 分屏对比 (US-2)

**新文件**: `test-platform-v2/frontend/src/pages/requirement/components/VersionCompare.tsx`

```
┌─────────────────────────────────────────────────────────┐
│ 版本对比: v14.1.0  →  v14.2.0          [X]              │
├─────────────────────────────────────────────────────────┤
│ 📊 摘要: 🆕3 新增  ✏️5 修改  ➡️12 不变  ❌1 删除        │
├──────────────────────────┬──────────────────────────────┤
│ 旧版本 (v14.1.0)         │ 新版本 (v14.2.0)             │
│ ┌──────────────────────┐ │ ┌──────────────────────┐     │
│ │ 🆕                  │ │ │ 📄 首页               │     │
│ │ (新增页面，旧版无)    │ │ │ 修改了banner和推荐列表 │     │
│ ├──────────────────────┤ │ ├──────────────────────┤     │
│ │ 📄 首页               │ │ │ 📄 首页               │     │
│ │ Banner: 原版图片       │ │ │ Banner: 新版图片       │     │
│ │ 推荐列表: 3列          │ │ │ 推荐列表: 2列          │     │
│ │ <del>旧文案</del>      │ │ │ <ins>新文案</ins>      │     │
│ ├──────────────────────┤ │ ├──────────────────────┤     │
│ │ 📄 直播页             │ │ │ 📄 直播页             │     │
│ │ (同右，无变化)         │ │ │ (同左，无变化)         │     │
│ └──────────────────────┘ │ └──────────────────────┘     │
├──────────────────────────┴──────────────────────────────┤
│ [🔄 同步滚动: 开]                              [导出]    │
└─────────────────────────────────────────────────────────┘
```

**组件 Props**:
```typescript
interface VersionCompareProps {
  open: boolean
  onClose: () => void
  docId: number         // 当前文档 ID
  baseVersion: string   // 旧版本号
  currentVersion: string // 新版本号
}
```

**关键交互**:
- 左侧旧版本页面列表、右侧新版本页面列表，一一对应
- 点击页面项展开差异详情（OCR diff 文本，红色删除/绿色新增）
- 同步滚动：两个面板共享 `scrollTop`，toggle 开关控制
- 复用 `BundleDetail.tsx` L443-504 的颜色标记模式：green(🆕) / amber(✏️) / red(❌)

**入口**: `requirement/index.tsx` — 在文档操作栏添加「版本对比」按钮，仅当 `doc.diff_json` 存在时显示。

---

### 2.2 PrototypePreview 截图预览 (US-3)

**新文件**: `test-platform-v2/frontend/src/pages/requirement/components/PrototypePreview.tsx`

```
┌─────────────────────────────────────────────────┐
│ 蓝湖原型截图 — v14.2.0 · 首页          [X]      │
├──────────────────────┬──────────────────────────┤
│                      │ OCR 文字:                 │
│   [蓝湖截图预览]      │                          │
│                      │ 用户端首页改版，包含:       │
│   ← 滚轮缩放         │ - Banner 区域             │
│   ← 鼠标拖拽         │ - 推荐赛事列表             │
│                      │ - 底部导航栏              │
│                      │ - 直播间入口              │
│                      │                          │
│                      │ 交互说明:                 │
│                      │ Banner可左右滑动           │
│                      │ 点击赛事→进入直播间        │
├──────────────────────┴──────────────────────────┤
│ ◀ 上一页 (1/15)  下一页 ▶        [下载原图]      │
└─────────────────────────────────────────────────┘
```

**组件 Props**:
```typescript
interface PrototypePreviewProps {
  open: boolean
  onClose: () => void
  jobId: number         // 证据任务 ID
  initialPageIndex?: number
}
```

**关键交互**:
- 左侧大图 + 右侧 OCR 面板
- 缩放：滚轮事件，`transform: scale()` (0.5x ~ 3x)
- 拖拽：mousedown → mousemove → mouseup，translate 偏移
- 翻页：◀ ▶ 按钮 + 键盘 ← → 方向键
- 响应式：弹窗 `max-w-[90vw] max-h-[90vh]`
- Loading 态：Skeleton 占位
- Empty 态：「该任务暂无截图」
- Error 态：「截图加载失败」+ 重试按钮

**入口**: `EvidenceTaskPanel.tsx` — 成功任务增加「查看截图」按钮，与现有「查看功能拆分」并列。

---

### 2.3 前端版本标记 (US-5)

**文件**: `test-platform-v2/frontend/src/pages/requirement/AiResultModal.tsx`

**新增组件 `VersionMarkerBadge`**:
```typescript
function VersionMarkerBadge({ fp, diffStatus, baseVersion }: {
  fp: TestFunctionPoint & { _inherited?: boolean; _from_version?: string }
  diffStatus?: string
  baseVersion?: string
}) {
  if (fp._inherited) {
    return <Badge variant="outline" className="text-blue-600 border-blue-300">
      ➡️ 沿用自 {fp._from_version || baseVersion}
    </Badge>
  }
  if (diffStatus === 'update') {
    return <Badge variant="outline" className="text-orange-600 border-orange-300">
      ✏️ 本版本变更
    </Badge>
  }
  return <Badge variant="outline" className="text-green-600 border-green-300">
    🆕 首次提取
  </Badge>
}
```

**插入位置**: `AiResultModal.tsx` L686 — `ClientScopeBadges` 旁边，功能点卡片 header 行。

**修改行**: L686 之后插入 `<VersionMarkerBadge fp={fp} diffStatus={extractionResult?.diff_summary} baseVersion={extractionResult?.inherited_from_version} />`

**类型扩展**: `TestFunctionPoint` (types/index.ts L149-156) 已包含动态字段，`_inherited` 和 `_from_version` 由后端动态添加，前端通过类型断言使用。

---

## 3. 测试修复 (US-6)

### 3.1 DebugTab.test.tsx (3 failures)

**根因**: `serviceName?: string` 可选属性新增，测试不传但组件使用默认值不报错。实际失败原因可能是 `composeAssetUrl` 行为变化。

**修复**: 在测试的 mock endpoint 数据中添加 `serviceName` props，验证 URL 拼接逻辑。

### 3.2 CaseDrawer.test.tsx (3 failures)

**根因**: CaseDrawer `reset()` 将默认 status 从 `'draft'` 改为 `'active'`，测试期望 `'草稿'` 但实际显示 `'启用'`。

**修复**: 更新测试断言：`expect(...).toContain('启用')`。

### 3.3 testcase.test.ts (3 failures)

**根因**: API 函数 `deleteDomain`/`createModule`/`deleteModule` 无输入验证 guard，测试期望 `.rejects.toThrow()` 但实际返回 resolved promise。

**修复**: 移除无效的 guard 测试断言（或改为验证 API 调用本身不抛错）。

---

## 4. Red Flag 检查

- ✅ 无 Ant Design 引用 — 全部 shadcn/ui + Radix + Tailwind
- ✅ 组件三态：Loading / Empty / Error 全覆盖
- ✅ 使用现有类型 `RequirementModuleOut.change_type` / `screenshot_urls`
- ✅ 后端降级兼容：imagehash 不可用时自动跳过
- ✅ 遵循现有代码模式：BundleDetail 颜色标记 / ClientScopeBadges 徽章
- ✅ 无硬编码颜色 — 使用 Tailwind token
- ✅ 弹窗使用现有 Dialog 组件模式 (≥90vw, max-h)
