# Batch 287 — Design / Dev

## 接口

```python
HttpRequestSpec(method, url, headers, params, json_body, content, timeout_ms)
HttpResult(ok, status_code, error, duration_ms, request, response)
HttpDriver.execute(spec) -> HttpResult
HttpDriver.execute_chain(specs, stop_on_failure=True) -> list[HttpResult]
```

## 证据结构

```json
request:  {method, url, headers(脱敏), json_body, params, timeout_ms,
           content_sha256, content_bytes}
response: {status_code, headers(脱敏), body(截断)}
```

- 敏感头：authorization / cookie / set-cookie / x-api-key / api-key / proxy-authorization → `***`；
- body 超过 `max_body_bytes`（默认 64KB）截断并加 `…[truncated]`；
- 网络错误：`error=TIMEOUT|<ExceptionName>`，`response={}`。

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-287-1 | driver 不做 retry | 首次失败必须可见；retry 由新 StepAttempt 表达 |
| D-287-2 | 证据内置脱敏/截断 | 防止凭据进 Artifact/日志 |
| D-287-3 | content 记 sha256 | 大 body 不重复存，可与 run_artifacts 关联 |
| D-287-4 | MockTransport 注入 client | 单测无外网、可复现 |
