# Batch 270 证据 — 版本号冲突时平台返回 500（登记 `C270-1`）

> 发现于本批真实演练（2026-09-20 18:11），不是构造场景。

## 1. 现象

驱动按 `--version-prefix 16.` 建版本任务时拿到 **HTTP 500**（裸内部错误），演练当场中断：

```
httpx.HTTPStatusError: Server error '500 Internal Server Error'
  for url 'http://127.0.0.1:8124/api/v1/version-tasks'
```

## 2. 最小复现（对着已存在的版本号再建一次）

```python
for ver in ("20.1", "20.1"):
    r = POST /api/v1/version-tasks {"title": "dup repro", "version": ver, "environment_id": 12}
    print(ver, "->", r.status_code, r.text)
```

```
20.1 -> 500 "Internal Server Error"
20.1 -> 500 "Internal Server Error"
```

## 3. 平台日志（试点平台 stderr，节选）

```
sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) UNIQUE constraint failed:
    version_task.project_id, version_task.version
[SQL: INSERT INTO version_task (project_id, title, version, source, ...) VALUES (...)]
[parameters: (1, '16.1 连续验收（drill）', '16.1', 'manual', None, None, ..., 12, 'draft', ...)]
```

即：`version_task` 有 `(project_id, version)` 唯一约束，但 `version_task_service.create_task` 没有把它转成业务错误，
直接冒泡成 500。

## 4. 影响（为什么值得登记，而不是"驱动换个前缀就行"）

| 面 | 影响 |
|----|------|
| 演练/复跑 | 同一版本系列跑第二次即 500；操作者只能猜"是不是服务坏了"（真实发生过：本批第一次跑就中断） |
| 其它调用方 | 平台自己的"版本验收"页面重复提交同名版本也会得到同样的 500 |
| 可诊断性 | 500 无业务码、无提示，违反本仓"查不到/冲突 → 业务码 + HTTP 200/4xx"的既有约定（见 `cameltv-bug-guard` 的 envelope 码铁律） |

## 5. 本批的处理（不越界）

- **驱动侧**：本批已加守卫——建版本任务返回 ≥400 时给出可操作提示（"请用 `--version-prefix` 换版本系列；不要删既有版本记录腾位置"），并有单测 `test_version_task_conflict_gives_actionable_error`；
- **平台侧**：**未改**（本批平台零改动）→ 登记 **`C270-1`（P2）**：建议 `create_task` 捕获完整性冲突并返回 `APIException(code=409/400, msg="版本号已存在")`，补一条回归测试。
- **本批演练改用** `--version-prefix 20.` 的**新系列**完成 3 版本（20.1/20.2/20.3），既有 16.x/17.x/18.x 记录一律未删。
