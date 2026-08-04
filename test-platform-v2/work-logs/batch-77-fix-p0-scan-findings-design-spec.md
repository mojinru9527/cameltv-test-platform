# Batch 77 — Design Spec（C76-1 存量 P0 修复）

> **Design (🎨)** | Date: 2026-08-04 | Status: 就绪

## 0. 技术体系确认

后端 FastAPI + Pydantic v2 + SQLAlchemy；无前端/API/Schema 变更（仅补 R 类方法）。

## 1. 变更设计

| 文件 | 改动 | 说明 |
|------|------|------|
| `app/schemas/common.py` | +`err()` classmethod | `code:int=1, msg:str="error"`，`data=None`，与 `ok()` 同构 |
| `app/seed.py` | +logging，5 处 print→logger.info | 密码行改为"已哈希存储（不输出明文）" |
| `app/api/v1/open_api.py` | +logging，3 处 except→logger.exception | CI 通知/线程启动失败可见 |
| `app/services/api_task_worker.py` | 2 处 except→logger.warning | 标记失败/DB 关闭失败可见 |
| `app/services/playwright_executor.py` | 1 处 except→logger.warning | 产物列表失败可见 |
| `tests/test_r_schema.py` | 新增 3 条单测 | err 默认/自定义/与 ok 同构 |
| `scripts/git/scan-common-bugs.ps1` | except-pass 带 `#` → WARN | 区分有意为之与真静默 |

## 2. R.err 接口契约

```python
@classmethod
def err(cls, code: int = 1, msg: str = "error") -> "R[T]":
    return cls(code=code, msg=msg, data=None)
```

- 调用点 7 处（test_case.py）零改动，继续 `R.err(code=404, msg=...)` 语义。
- 与 `R.ok` 同构 → 前端 envelope `{code,msg,data}` 契约不变。

## 3. 日志改造清单（6 处）

| 文件:行(原) | 场景 | 日志级别 | 内容 |
|------------|------|---------|------|
| open_api.py:116 | CI 触发通知失败 | exception | plan_id |
| open_api.py:222 | CI 结果回写通知失败 | exception | run_id |
| open_api.py:307 | Playwright 线程启动失败 | exception | run_id/job_id |
| api_task_worker.py:224 | 标记失败静默 | warning | 描述 |
| api_task_worker.py:297 | DB 关闭失败 | warning | 描述 |
| playwright_executor.py:543 | 产物列表失败 | warning | 返回部分结果说明 |

## 4. 扫描规则细化

- except-pass 匹配后，把匹配段扩展到行尾，若含 `#` → WARN（有意为之，需人工复核）；无注释 → HARD（真静默）。
- SelfTest 夹具无注释吞异常 → 仍 HARD，断言不变。

## 5. 设计 QA 走查发现

### ⚪ P3-01 本地 Python 环境损坏
基础 Python 3.12 被卸载、两个 venv 失效、runner Python 位置异常 → 本地 pytest 阻塞；**建议**：本批由 CI 全量回归兜底并如实记录，后续批次修复开发机 Python 环境（C77-2）。

## 6. 设计签核

结论：通过（P3-01 为环境阻塞，记录不阻断）。
