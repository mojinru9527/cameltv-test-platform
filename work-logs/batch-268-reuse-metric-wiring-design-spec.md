# Batch 268 Design — 埋点接线与测量来源

> **Design/Dev** | Date: 2026-09-20

## 1. 接线点与粒度

```
create_task(...)
  → db.add(task); commit; refresh
  → for suggestion in get_reuse_suggestions(db, project_id):
        for title in suggestion["reuse"]:                      # 条目粒度
            record_suggestion(project_id, task_id=task.id,
                              suggestion_ref=f"knowledge:{suggestion['id']}:{title}",
                              title=title)
```

- **为什么是"建任务时"**：B3-4 的定义是"**建任务时自动带出**上版复用建议"——带出即视为"被建议过"，这是分母的语义时刻。
- **为什么是条目粒度**：`hit_rate` 要回答"带出的复用条目里有多少被真正复用"，所以分子分母都应按条目。
- **不吞异常**：`record_suggestion` 是普通插入；失败说明真有 bug，冒泡比静默更安全（history: S7 静默吞异常曾被登记）。

## 2. 驱动测量来源

```
run_versions(...):
  reuse_suggested, reuse_adopted = args.reuse_suggested, args.reuse_adopted   # 人工口径（回退）
  if not reuse_suggested and not reuse_adopted:
      reuse_suggested, reuse_adopted = _platform_reuse_stats(client, headers) # 平台口径（优先）
      reuse_source = "platform"
  报告里带 reuse_source，避免"数字来源不明"
```

`_platform_reuse_stats` 对非 200 与 httpx 异常一律回退 `(0, 0)`（宁可报告"无数据"，也不编数字）。
