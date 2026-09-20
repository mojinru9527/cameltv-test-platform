# Batch 269 证据 — 控制面"不存被测系统凭据"核对（2026-09-20，只读）

> 对应约束：`docs/platform-refactor/10-landing-plan-task-backlog.md` §4-1 与 `09-platform-landing-plan.md` 职责边界。
> 对象：本机试点控制面（`127.0.0.1:8124`）的试点库 `probe.db`，取 Batch 269 演练登记的 6 个执行任务（job 46–51）。

## 1. 执行任务 payload 凭据扫描

```python
pat = re.compile(r"(authorization|password|passwd|secret|token|cookie|api[_-]?key|bearer)", re.I)
for jid, kind, payload in con.execute("select id, kind, payload_json from execution_jobs where id between 46 and 51 order by id"):
    hits = sorted(set(m.group(0).lower() for m in pat.finditer(payload)))
    print(jid, kind, len(payload), hits)
```

```
job 46 kind=api payload_bytes= 16911 credential_like_tokens=[]
job 47 kind=web payload_bytes=  9029 credential_like_tokens=[]
job 48 kind=api payload_bytes= 16911 credential_like_tokens=[]
job 49 kind=web payload_bytes=  9029 credential_like_tokens=[]
job 50 kind=api payload_bytes= 16911 credential_like_tokens=[]
job 51 kind=web payload_bytes=  9029 credential_like_tokens=[]
```

**结论**：6 个任务的完整 payload 里**没有任何凭据类字段**。payload 只含 `base_url` + `cases`（接口：`request{method,url,headers,body}` + `assertions`；Web：`steps[{action,...}]`），其中 `headers` 实测只有 `Content-Type: application/json`。

## 2. 平台侧的"槽位"与"密钥引用"

```sql
select count(*) from secret_refs;          -- 0
pragma table_info(secret_refs);            -- id, project_id, name, provider, external_ref, purpose, scope_json, status, rotated_at, created_at
select name from sqlite_master where type='table' and name like '%slot%';   -- （无）
```

**结论**：

1. `secret_refs` **0 行**，且其 schema 存的是 `external_ref`（**外部引用**）而不是密钥值——设计上符合"控制面不存被测系统凭据"；
2. 平台库里**没有**"账号槽位"表：驱动传的 `--account-slot sports-tester-01` 只是一个**标签**（写进 `execution_jobs.env_ref`），不是凭据；
3. 被测系统方面：Test5 试点端点为匿名 GET（无鉴权），故这条链路上**不存在**被测系统凭据。

## 3. 浏览器到底在哪跑

| 事实 | 证据 |
|------|------|
| Web 用例由**节点**执行 | 3 个 Web job 的 `node_id = pilot-node`；截图与 console 落在**节点**工作目录 `C:\Users\26029\AppData\Local\Temp\cameltv-ops\nodehome9\work\job-{47,49,51}-attempt-1\case-*.png|console.json` |
| 平台只登记/派发 | 平台侧只有 `execution_jobs` 行 + 证据包（上传后的 manifest/sha256），没有浏览器进程 |
| 本轮无模型调用 | 演练路径为 `drill_three_versions.py → execution-jobs → node`，未触发任何 AI/模型端点 |

## 4. 保留项（不掩盖）

控制面仍保留 `/uitest` 的内置浏览器执行路径（`app/services/playwright_executor.py` + `ui_test_service.execute_playwright_async`），与 09 §3.1「控制面 ❌ 跑浏览器」的**终态**有张力。Batch 263 已裁定**保留**（它已不是执行队列；执行面由 `ExecutionJob` + `cameltv-node` 承接）并登记 `C263-1` 承接收口。本报告不把它算作"已满足"，只标注保留。
