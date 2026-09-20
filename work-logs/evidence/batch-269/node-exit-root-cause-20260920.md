# Batch 269 证据 — 节点进程退出的根因定位（C269-3，2026-09-20）

> 背景：Batch 269 演练期间，平台重启后节点进程消失、无日志，job 46/47 停在 `pending` 约 3 分钟，直到人工重启节点才继续。
> 本文件把"原因未知"变成"机制已定位 + 可复现"。

## 1. 结论

**节点的轮询循环只捕获 `TransportDown`（网络不可达），任何 HTTP 4xx/5xx 或非零业务码都会让 `call()` 抛 `SystemExit(2)` 直接结束进程** —— 且 `SystemExit` 不打 traceback，只在 stderr 留一行 `ERROR POST /execution-jobs/claim -> HTTP …`，表现就是"节点无声消失、任务卡在 pending"。

```python
# scripts/node/cameltv_node/cli.py — call()（节选）
if resp.status_code >= 400 or payload.get("code") not in (None, 0):
    print(f"ERROR {method} {path} -> HTTP {resp.status_code} code={payload.get('code')} …", file=sys.stderr)
    raise SystemExit(2)          # ← 非网络错误 = 直接退进程

# scripts/node/cameltv_node/cli.py — _loop()（节选）：唯一的 except 是 TransportDown
    while True:
        try:
            job = _claim(cfg)          # ← _claim 直接调 call()，没有兜 SystemExit
        except TransportDown as exc:
            print(f"[warn] {exc}；{args.poll_seconds}s 后重试（任务不会被判失败）", file=sys.stderr)
            time.sleep(args.poll_seconds)
            continue
```

`_heartbeat_once()` 反而是**对的**（它 `except SystemExit: return False`，所以心跳期间的 4xx 不会杀进程）——同一份代码里两种处理并存，说明这是遗漏而非设计。

## 2. 复现（把 `httpx.request` 换成桩，三种场景对照）

```python
cli.httpx.request = fake            # A: 抛 ConnectError；B/C: 返回 500/403
cli._claim(cfg)                     # 观察抛出的异常类型
```

```
场景 A：平台不可达（连接被拒）
  A: TransportDown（可被轮询循环捕获并重试）→ 平台不可达: ConnectError: connection refused
场景 B：平台返回 HTTP 500
  B: **SystemExit(2)** —— 轮询循环 _loop 未捕获 → 进程直接退出
场景 C：平台返回 HTTP 403
  C: **SystemExit(2)** —— 轮询循环 _loop 未捕获 → 进程直接退出
--- _loop 的异常处理面 ---
    job = _claim(cfg)
    except TransportDown as exc:
    except TransportDown as exc:
```

（桩只替换 `httpx.request`，其余代码路径都是仓库里真实的 `cli.py`；运行输出里的两行 `ERROR POST /execution-jobs/claim -> HTTP 500/403 …` 是 `call()` 自己打印的，与线上现象一致。）

## 3. 为什么这能解释演练当天的现象

| 现象 | 本机制的解释 |
|------|-------------|
| 节点进程消失、没有 traceback | `SystemExit` 不打印调用栈，只留一行 ERROR；而当天该节点没有落日志文件（控制台随上一个会话丢失），所以"无日志" |
| 发生在平台重启窗口附近 | 平台重启期间/刚起来时对 `POST /execution-jobs/claim` 返回 5xx（或鉴权/项目头类 4xx）即触发；网络层被拒反而是安全的（TransportDown 会重试） |
| job 46/47 停在 `pending` 而不是 `failed` | 节点没认领成功就退出了，任务从未进入 running；平台租约机制无关（这正是"协议层没问题、进程自愈有问题"） |

**如实标注**：这是**机制级复现 + 与现象一致的解释**，不是"当天那次退出的逐帧日志"（那台节点的 stderr 没有落盘，无法回看）。要 100% 闭合，需要在修复后做一次"平台重启 → 节点应自动重连"的实测。

## 4. 修复方向（登记到 `C269-3`，下批实施）

1. 轮询循环把"平台返回错误"与"平台不可达"统一按**可恢复**处理：`call()` 只对**真正致命**的情况（如 401 鉴权失败且不可恢复）退出，其余按退避重试；
2. 连续失败要有**上限与可读日志**（当前是"一次就死"），并保证异常退出也留日志/退出码语义；
3. 补回归：把本文件的三场景写成测试（A→重试、B/C→不退出），避免再次出现"一次 500 就自杀"。
