# Batch 307 — Design / Dev / QA

## 组件

```tsx
<PlatformMatrix rows={[{ ac_id, ac_text, semantic_type?, bindings: [{
  platform, build, device, profile, actual, evidence[]
}]}]} />
```

- 平台列由所有 bindings 去重生成（web/h5/miniapp/android/ios）；
- 单元格：actual + `build · device · profile` + evidence chips；
- 缺失平台 `—`；无数据空态。

## 测试

- 2 条 vitest：多端独立数据 + 语义类型；缺失/空态；
- 前端全量 560 passed；typecheck/build 通过。

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-307-1 | 平台列动态生成 | 不同 AC 覆盖端不同，不写死 |
| D-307-2 | 语义类型放 AC 行 | 跨端语义是 AC 级属性 |
| D-307-3 | 证据仅展示引用 | 与 Run 证据链一致，不复制文件 |

## 文件

- `frontend/src/pages/defect/PlatformMatrix.tsx`
- `frontend/src/pages/defect/__tests__/PlatformMatrix.test.tsx`
