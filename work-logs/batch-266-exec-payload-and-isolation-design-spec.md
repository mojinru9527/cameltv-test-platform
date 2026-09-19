# Batch 266 Design — 断言语义 / 用例隔离 / payload 构造

> **Design/Dev** | Date: 2026-09-19

## 1. 断言求值（`scripts/node/cameltv_node/executor.py::evaluate_assertions`）

```
kind ∈ {status, status_code} + operator ∈ {eq,gte,gt,lte,lt}   → 状态码比较（未知算子 → 失败）
kind ∈ {json_path, jsonpath}                                  → expected=null 视为"存在性"，否则等值
kind == response_time                                         → elapsed_ms ≤ expected（毫秒）
其余未被识别的 kind                                            → 失败（保持 fail-loud）
```

新增入参 `elapsed_ms`，由 `_run_one_api_case` 从 `response.elapsed` 传入（缺失即不通过）。

## 2. Web 用例隔离与健壮性（`run_web_cases` / `_run_one_web_case`）

- **隔离**：由"一个 job 一个 context"改为 **每条用例一个 `factory()`**（真实实现里是一次 `chromium.launch()`+`new_context()`），执行完即关闭 → 用例间不共享 cookie/localStorage。
- **健壮性**：① 单条用例异常被捕获并记为该用例失败（`error` 字段），不冒泡拖垮 job；② 单个步骤异常收敛为"该用例失败"并记录步骤号与动作。
- **可见性语义统一**：`expect_visible` 由 `page.is_visible(selector)`（首个匹配）改为 `_any_visible(page, selector)`（任一匹配可见，与 `wait_visible` 一致）；对不实现 `locator` 的替身页面回退到旧语义。

## 3. 驱动 payload（`test-platform-v2/backend/scripts/drill_three_versions.py`）

```
_load_executable_cases(args, dataset) → (api_cases, web_cases, unexecutable)
  api  : 按 case.id 取 TestCase → {id:"case:<id>", request:{method,url,headers,body}, assertions: api_assertions}
  web  : 取 TestCase.steps 中带 action 的对象；无 action 视为不可执行
  unexecutable 非空 → SystemExit（列出用例，绝不空跑）
新增 --web-target-url（Web 基址，默认同 --target-url）
```

## 4. 用例集口径修正

`SP-WEB-013` / `SP-WEB-028`（新闻页）原断言 `text=Home` 命中的是**隐藏链接**（实测 `wait_for_selector` 超时）→ 改为断言新闻卡片 `a[href^="/news/detail/"]` 可见（实测两站均有该锚点）。
