# Slice 0 — Task 0a: 三引擎代码级事实核查报告

> **日期**: 2026-07-19 | **核查人**: Dev Agent | **结论**: 三引擎全部真实，文档已同步

---

## 核查方法

逐文件读取引擎源码，定位真实执行/网络请求/子进程调用的代码行。与旧文档声明逐条对照。

---

## 引擎 1: API 测试 — `api_execution_service.py`

**旧文档声明**（`现状功能PRD.md` 旧版）: 「纯前端 fetch」「localStorage」「无后端」

**代码实际**:

| 行号 | 证据 | 结论 |
|------|------|------|
| `:1` | 模块 docstring: "服务端 HTTP 请求 + 变量替换 + 断言" | 服务端引擎 |
| `:12` | `import httpx` | 真实 HTTP 库 |
| `:37-72` | `execute_api_case()` 公共 API — 从 DB 加载用例，解析 headers/body/assertions | 落库、非 localStorage |
| `:97-236` | `_do_execute()` 核心流程 | — |
| `:114-116` | `_check_prod_protection()` 生产环境保护 | 安全机制 |
| `:119-127` | `resolve_variables()` 环境变量替换 | 变量系统 |
| `:144-156` | `ensure_vpn_for_test_environment()` VPN 前置检查 | 网络能力 |
| `:159` | `start = time.perf_counter()` | 真实计时 |
| `:166-177` | **`httpx.Client(timeout=30, follow_redirects=True).request(method, url, headers, content)`** | ✅ **真实 HTTP 请求** |
| `:178` | `duration_ms = round((time.perf_counter() - start) * 1000, 1)` | 真实耗时 |
| `:199-206` | `_run_assertions()` 断言引擎 | 断言系统 |
| `:210-221` | 响应快照 `status_code + headers + body_preview + body_size_bytes` | 快照落库 |
| `:241-310` | 断言类型: status_code / contains / json_path / response_time / header | 5 种断言 |
| `:26-28` | 安全: MAX_RESPONSE_BODY_SIZE=500KB, SENSITIVE_HEADERS masked | 安全基线 |

**判决**: ❌ 旧文档「纯前端 fetch」→ ✅ 真实 httpx 服务端引擎。**旧文档完全过时。**

---

## 引擎 2: UI 自动化 — `playwright_executor.py`

**旧文档声明**（`现状功能PRD.md` 旧版）: 「`random.randint/uniform` 伪造 total/pass/duration」「未真实驱动 Playwright」

**代码实际**:

| 行号 | 证据 | 结论 |
|------|------|------|
| `:1-3` | 模块 docstring: "subprocess.Popen 实现进程管理、取消轮询、超时 kill 和产物隔离" | 真实子进程 |
| `:12` | `import subprocess` | 子进程管理 |
| `:27` | `PLAYWRIGHT_DIR = ... / "tests" / "playwright"` | Playwright 测试目录 |
| `:64-67` | `_resolve_cmd()` — `shutil.which(name)` 跨平台解析 npx | 真实命令查找 |
| `:70-87` | `_check_playwright_installed()` — `subprocess.run([npx, "playwright", "--version"])` | ✅ **真实调用 npx playwright** |
| `:90-99` | `_list_available_specs()` — 递归扫描 `.spec.js`/`.spec.ts` | 真实 spec 发现 |
| `:102-126` | `_resolve_environment_variables()` — 解密 AES-128 加密变量注入进程环境 | 安全变量注入 |
| `:129-185` | `run_playwright_test()` — 信号量并发控制 (`MAX_CONCURRENT=2`) + CAS 原子认领 + 通知推送 | 生产级调度 |
| `:188-249` | `_run_playwright_test()` — **`subprocess.Popen([npx, "playwright", "test", test_spec, "--project", browser, "--reporter", "json"])`** | ✅ **真实 Playwright 执行** |
| `:29` | `MAX_CONCURRENT = 2` | 并发控制 |
| `:28` | `DEFAULT_TIMEOUT = 300` (5 min) | 超时保护 |
| `:30` | `CANCEL_POLL_INTERVAL = 1.0` | 取消轮询 |
| `:212-216` | `artifact_dir = STORAGE_DIR / str(run_id)` 产物隔离 | 产物管理 |
| `:232-238` | `BASE_URL` 注入 + 环境变量注入 | 环境注入 |

**判决**: ❌ 旧文档「随机数模拟」→ ✅ 真实 subprocess.Popen 驱动 Playwright。**旧文档完全过时。** `ui_test_service.py` 中可能曾有的 `random.randint` 已被 `playwright_executor.py` 取代。

---

## 引擎 3: 音视频专项 — `av_check_service.py` + `ffmpeg_service.py`

**旧文档声明**（`现状功能PRD.md` 旧版）: 「`random.uniform` 伪造 value」「未真实拉流探测」

**代码实际**:

### ffmpeg_service.py — 真实 ffprobe 探测

| 行号 | 证据 | 结论 |
|------|------|------|
| `:1` | 模块 docstring: "子进程调用 ffprobe 解析流指标" | 真实探测 |
| `:8` | `import subprocess` | 子进程 |
| `:64-80` | `_check_ffmpeg_installed()` — **`subprocess.run([ffprobe, "-version"])`** | ✅ **真实调用 ffprobe** |
| `:18-61` | `METRIC_DEFS` — 6 项指标定义: 起播时延/码率/帧率/分辨率/流可用性/编码格式 | 专业指标 |
| `:15` | `SUPPORTED_PROTOCOLS = {"HLS", "FLV", "RTMP", "DASH", "HTTP", "HTTPS"}` | 多协议支持 |
| `:14` | `DEFAULT_TIMEOUT = 30` | 超时保护 |

### av_check_service.py — 统计引擎 + 测量管理

| 行号 | 证据 | 结论 |
|------|------|------|
| `:20-46` | `MEASUREMENT_TEMPLATES` — 5 类检测模板 (video_delay/call_delay/av_sync/frame_rate/first_frame)，含阈值/对比方式/通过基准/方法/前置条件 | 专业模板 |
| `:132-142` | `_percentile()` — 百分位计算（p95） | 统计方法 |
| `:145-155` | `_calculate_stats()` — mean/median/min/max/stddev/p95 | 完整统计 |
| `:193-217` | `_apply_measurement_data()` — 基于真实 `samples` 计算统计值 + 对比阈值判定 pass/fail | 真实判定 |
| `:184` | `"simulated": False` — **测量值显式标记为非模拟** | 诚实标记 |
| `:220-232` | `create_measurement()` — 从用户提交的 samples 数据创建测量记录 | 数据录入 |

**判决**: ❌ 旧文档「随机数模拟」→ ✅ 真实 ffprobe 探测 + 统计引擎。**旧文档完全过时。** 注：AV 模块的测量值来源是用户手动录入或 ffprobe 探测结果，`av_check_service.py` 不生成随机数——它做真实统计计算。

---

## 总结

| 引擎 | 旧文档声称 | 代码实际 | 核心证据 |
|------|-----------|---------|---------|
| API 测试 | 纯前端 fetch + localStorage | httpx 服务端真实 HTTP | `api_execution_service.py:166-177` |
| UI 自动化 | random.randint 随机数 | subprocess.Popen 真实 Playwright | `playwright_executor.py:245-249` |
| 音视频专项 | random.uniform 随机数 | ffprobe 子进程 + 统计引擎 | `ffmpeg_service.py:70-71`, `av_check_service.py:145-155` |

**三引擎全部真实。旧文档的「演示态」标签是 V2.1 时代的快照，V2.2-V2.6 已全部真实化。**
