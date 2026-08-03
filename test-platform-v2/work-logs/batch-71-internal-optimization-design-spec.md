# Batch 71 — Design Spec（内部收尾优化）

> **Design (🎨)** | Date: 2026-08-04

## 1. C70-3 登录限流环境化

```python
# core/config.py
login_rate_limit_max: int = 10
login_rate_limit_window_seconds: int = 900

@property
def effective_login_rate_limit(self) -> tuple[int, int]:
    if self.environment in ("development", "test"):
        return max(self.login_rate_limit_max, 100), self.login_rate_limit_window_seconds
    return self.login_rate_limit_max, self.login_rate_limit_window_seconds
```

- `rate_limit.py`：`login_limiter = RateLimiter(*settings.effective_login_rate_limit)` 改为函数或按需构造。
- `.env.example` 增加注释行（生产保持 10/900，dev 可放宽）。

## 2. C69-3 分批并发

```python
_CHUNK_CONCURRENCY = 2
sem = asyncio.Semaphore(_CHUNK_CONCURRENCY)

async def _run_chunk(i, chunk):
    async with sem:
        ...截断重试...
        return (i, result_or_None, warning)

results = await asyncio.gather(*[_run_chunk(i, c) for i, c in enumerate(chunks, 1)])
按 i 排序合并 functional_cases；失败块告警；全部失败 → ValueError
```

## 3. C70-2 报告模板增强

- 行内「设为默认」：Switch → `updateTemplate(id, {is_default: true})`，其余模板 is_default 由后端归一。
- 章节编辑：编辑对话框展示 sections 列表（key/label/enabled），勾选保存。

## 4. C65-2 手册删除

- 审计引用：`rg "双VPN|固定配置" docs work-logs`；删除目标文件；更新引用链接；跑 `cameltv-doc-check`。
