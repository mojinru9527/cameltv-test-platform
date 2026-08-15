# 🗂️ Dev 部门项目看板 — batch-185-perf-collector-optimize

> Batch 185（完整）：C99-1 性能采集优化 ①②③（并行采样/jank 口径/CPU 语义）

---

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | batch-185-perf-collector-optimize |
| **关联 PRD** | test-platform-v2/work-logs/batch-185-perf-collector-optimize-prd-summary.md |
| **看板创建** | 2026-08-16 |

---

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 0 | 工件 PRD/PM/Design/看板 | ✅ | ✅ | ✅ | ⏳ | ⏳ | commit 7263d80 |
| 1 | 并行采样 + jank 口径 + CPU 配置 | ✅ | ✅ | ✅ | ⏳ | ⏳ | 66 例 perf 测试绿 |
| 2 | iOS collectX 语义修复（测试暴露） | ✅ | ✅ | ✅ | ⏳ | ⏳ | |
| 3 | QA/Leader + C99-1 ①②③ 关闭 | ✅ | ✅ | ✅ | ⏳ | ⏳ | commit b16d9de；全量 1544/0 |
| 4 | 总确认 → push → PR → 合入 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | |

---

## 📍 当前位置

```
Batch 185 — 待总确认
├── 已完成: 全部实现与证据（1544/0 + perf 66 例）
└── ⏳ 下一步: 用户一次总确认 → push → Draft PR → checks 全绿 → 合入
```
