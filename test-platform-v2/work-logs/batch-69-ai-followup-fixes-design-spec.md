# Batch 69 — Design Spec（AI 验收跟进修复）

> **Design (🎨)** | Date: 2026-08-03

## 1. C68-2 — TestCaseUpdate.source_doc_id

### 改动
```python
class TestCaseUpdate(BaseModel):
    ...
    source_doc_id: Optional[int] = None
```

### 校验（update_case 前置）
- `source_doc_id` 非空时：`requirement_service.get_requirement(db, doc_id, project_id=current.project_id)` 不存在
  → 400「来源需求文档不存在或无权关联」。
- 无 `source_doc_id` 字段时行为不变（保持向后兼容）。

### 证据路径
`PUT /api/v1/test-cases/{id}` → `GET /api/v1/trace/requirement/{doc_id}` 计数变化；DB `source_doc_id` 落库。

## 2. C68-3 — 分批生成

### 触发条件
`extraction.modules` 存在且功能点总数 > `CASE_GENERATION_CHUNK_FP_LIMIT`（默认 25）。

### 流程
```
chunks = split_modules_by_fp(modules, limit=25)   # 保序；单模块 FP>limit 时按 FP 再切
for chunk in chunks:
    user_message = _build_user_message_with_extraction(content, file_type, source_ref, {modules: chunk})
    resp = await _call_ai_api(functional_system, user_message, f"functional-chunk-{i}")
    if resp.truncated and retry==0: resp = await _call_ai_api(...)   # 重试 1 次
    if resp.result: merge functional_cases
    else: warnings.append(...)   # 不整体失败
```

### 合并规则
- 每块用例追加到同一 functional_cases 列表；用例编号由服务端统一重新编号（保持唯一）。
- 任一块失败仅告警该块，成功块照常返回；warnings 透出到响应。
- 全部块失败 → 保留原行为（400 + 原始响应保存）。

### 配置
`ai_service` 内常量 `_CHUNK_FP_LIMIT = 25`（无需 env，减少配置面）。

## 3. C68-4 — 发布决策登记

生产交付清单新增「正式域名发布演练（batch-68）」小节：结论（Vercel /login、/、/api 200；Railway health 200）、
决策项（1. 是否继续使用 `cameltv-test-platform1.vercel.app`；2. 是否启用自定义域名/Cloudflare 豁免；3. ALLOWED_ORIGINS 已对齐）。

## 4. 测试计划

| 用例 | 类型 | 断言 |
|------|------|------|
| update_case 接受 source_doc_id | 单测 | DB 落库 + 越权文档 400 |
| generate 单块（≤25 FP） | 单测(mock) | 1 次 AI 调用，行为不变 |
| generate 大文档（>25 FP） | 单测(mock) | 多次调用、用例合并、编号唯一 |
| generate 块截断 | 单测(mock) | 重试 1 次；仍失败仅告警该块，其余块保留 |
| 端到端 147 FP 文档 | 平台实测 | generate 200 + functional_cases 非空 |
