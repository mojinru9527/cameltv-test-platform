# 🗂️ Dev 部门项目看板

> **用途**：追踪多批次开发的进度节点，防止上下文丢失。每次 Dev 部门启动时**必须先读取本看板**。

---

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | 测试基础设施修复（共享夹具 + 前端构建） |
| **关联 PM 计划** | N/A（技术债修复，用户直派 DEV） |
| **关联 PRD** | N/A |
| **总预估工时** | 3.1h |
| **已用批次** | 4 批 |
| **看板创建** | 2026-07-09 |
| **最后更新** | 2026-07-09 |

---

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 后端共享夹具修复（StaticPool + token→access_token） | ✅ | ✅ | ✅ | ✅ | ⏳ | auth 12/12 通过 |
| 2 | auth 测试体漂移修复（3 处断言/夹具依赖） | ✅ | ✅ | ✅ | ✅ | ⏳ | 同源登录响应漂移 |
| 3 | 前端 17 处类型错误修复（trace/dataset/integration） | ✅ | ✅ | ✅ | ✅ | ⏳ | tsc -b 归零 |
| 4 | 隔离孤儿/测试文件（TemplateManager + *.test.ts） | ✅ | ✅ | ✅ | ✅ | ⏳ | tsconfig exclude |
| 5 | drift 1 路由顺序修复（静态 /batch 前置于 /{case_id}） | ✅ | ✅ | ✅ | ✅ | ⏳ | QA 判定=端点 bug；纯搬移零逻辑变更 |
| 6 | drift 2 测试改调真实端点 auto-execute | ✅ | ✅ | ✅ | ✅ | ⏳ | QA 判定=测试陈旧 |
| 7 | drift 3 删除断言对齐 envelope（200+code=404） | ✅ | ✅ | ✅ | ✅ | ⏳ | QA 判定=测试陈旧（硬删生效） |
| 8 | 第二波簇1：登录体漂移 token→access_token / username→user.username（6 例） | ✅ | ✅ | ✅ | ✅ | ⏳ | QA=测试陈旧，同源 |
| 9 | 第二波簇2：test_login_sets_cookie/includes_token 补 admin_user 夹具（2 例） | ✅ | ✅ | ✅ | ✅ | ⏳ | QA=夹具缺失 |
| 10 | 第二波簇3：/notify/ → /notify/channels（2 例） | ✅ | ✅ | ✅ | ✅ | ⏳ | QA=测试陈旧，真实端点是 /channels |
| 11 | 第二波簇4a：trace trend 断言 points→trend | ✅ | ✅ | ✅ | ✅ | ⏳ | QA=测试陈旧，真实键是 trend |
| 12 | 第二波簇4c：v26/v27 smoke 脚本式结构修复（误采集/采集中断） | ✅ | ✅ | ✅ | ✅ | ⏳ | test_connection 别名导入 + R4c 特性守卫 |
| 13 | test_authorization_header_fallback：清 cookie jar 隔离头回退 | ✅ | ✅ | ✅ | ✅ | ⏳ | QA=测试缺陷（端点正确，cookie 抢先） |
| 14 | Feature A：AI 超时降级到本地模块提取（config 字段 + retry + _local_extract_modules） | ✅ | ✅ | ✅ | ✅ | ⏳ | Batch 4，用户确认实现 |
| 15 | Feature B (R4c)：ReportCreate/TestReport 导入 template_id（model 列 + schema 字段） | ✅ | ✅ | ✅ | ✅ | ⏳ | Batch 4，迁移已在 0009 中 |
| 16 | Feature B (R4c)：create_report 服务挂接 template（校验→存储→sections 注入） | ✅ | ✅ | ✅ | ✅ | ⏳ | +3 行为测试验证 |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

---

## 📍 当前位置

```
Batch #4 — 两处未实现特性落地（用户确认实现：AI 超时降级 + R4c 报告模板挂接）
├── 已完成: Feature A（ai fallback）+ Feature B（R4c 挂接），全套件 179 passed / 0 skipped / 0 failed
├── 🔄 进行中: 无
├── ✅ 已审批: 用户 Review 通过（2026-07-09）
├── ⏳ 待合入: PR #17 等待 merge
└── ⏳ 待产品判定: 无（Batch 3 的两处 flag 已应用户确认实现并转绿）
```

---

## 📜 批次记录

### Batch 4 — 两处未实现特性落地（用户确认实现）(2026-07-09)
- **背景**：Batch 3 将两处未实现特性 skip+flag 交产品判定。用户回复「确认要做，你可直接接手补 config 字段+服务分支 / schema 字段+模型列+迁移」→ DEV 接手实现。
- **Feature A — AI 超时降级到本地模块提取**（真·新特性，非改测试）：
  - `app/core/config.py`：新增 `ai_timeout_seconds`(180.0) / `ai_retry_attempts`(2) / `ai_fallback_on_failure`(True)。
  - `app/services/ai_service.py::_call_ai_api`：超时改用 `settings.ai_timeout_seconds`（原硬编码 180.0）；加重试循环（瞬时失败 timeout/network 重试 `ai_retry_attempts` 次）；返回 `failure_kind`（None/timeout/network/parse/config）供上层判断是否降级。⚠️ `httpx.TimeoutException` 必须先于 `httpx.HTTPError` 捕获（前者是后者子类）。
  - `app/services/ai_service.py::_local_extract_modules`（新增）：无 LLM 的本地启发式拆分——按「页面/模块/功能/系统/中心/管理/流程/设置/配置」结尾或 `#` 前缀识别模块头，其余行作为功能点，输出与 AI 提取同 schema（modules[].function_points[]），每个功能点标注「待人工复核」。
  - `app/services/ai_service.py::extract_features`：`_call_ai_api` 失败且 `failure_kind∈{timeout,network}` 且 `ai_fallback_on_failure` → 降级返回 `fallback_used=True` + `extraction_progress=1.0` + 本地草稿；**parse/config 失败仍走原 detailed raise（不掩盖真 AI 契约破损）**。成功路径也补 `fallback_used=False`/`extraction_progress=1.0`。
  - `tests/test_ai_extraction_fallback.py`：去 skip 转绿（1 passed）。⚠️ 期间有 hook 二次改写重加 module 级 skip 并删掉 `settings`/`extract_features` 导入，已 Write 重写恢复可运行版本。
- **Feature B — R4c 报告模板挂接**（新特性）：
  - **发现迁移已存在**：`alembic/versions/20260702_0009_test_report_template_id.py` 早已幂等添加 `test_report.template_id` 列且在 head 链上（R4d 校验已覆盖）→ **无需新建迁移**，只缺 model/schema/service 三层。
  - `app/models/test_report.py`：补 `template_id: Mapped[int|None]`（nullable，无 FK 约束，与迁移一致）。
  - `app/schemas/test_report.py`：`ReportCreate` + `ReportOut` 补 `template_id: Optional[int]=None`。
  - `app/services/report_service.py::create_report`：`template_id` 提供时→ 校验模板属本项目（不存在则 `raise ValueError("报告模板不存在")`，不静默忽略）→ 存 `template_id` 列 → **非破坏性**注入 `content["sections"]`（按 order 升序的 enabled 板块）+ `template_id`/`template_name`（原始快照数据全保留）。`get_report`/`list_reports`/create 返回补 `template_id`。
  - `tests/test_v27_smoke.py`：R4c 段特性守卫 → 硬断言（特性已实现）。
  - `tests/test_report_template_attach.py`（新增 3 例）：验证服务路径——挂接存 id+注入有序 enabled sections / 无 template_id→None 且不注入 sections / 未知 template_id→ValueError。
- **产出**（生产码 5 + 测试 3）：`config.py`、`ai_service.py`、`models/test_report.py`、`schemas/test_report.py`、`report_service.py`；`test_ai_extraction_fallback.py`、`test_v27_smoke.py`、`test_report_template_attach.py`。
- **验证**：`pytest -q`（全套件）→ **179 passed / 0 skipped / 0 failed / 0 error**（Batch 3 末 175 passed/1 skipped → 去 skip +1、R4c 行为测试 +3）。
- **遗留（前端，非本批）**：`frontend` 报告类型未加 `template_id`（可选字段，向后兼容，不阻断）；如需前端选模板下拉需另起前端切片。
- **审批**: ✅ 用户 Review 通过（2026-07-09）
- **耗时**: ~50min

### Batch 3 — 第二波暴露的 10 处失败 + 1 采集中断 (2026-07-09)
- **背景**：Batch 1 夹具修好后，登录依赖套件才真正跑起来，暴露各自既有漂移。用户指示此类问题「主见发现就修，修完一个接着下一个，不逐个询问」（见 [[feedback-autonomous-drift-fixing]]）。
- **QA 三态化判定 + DEV 处置**：
  - 簇1 登录体漂移（6 例，`test_critical_path` + `test_p1_security_regression`）→ **测试陈旧**：`token`→`access_token`（LoginOut 字段名）、`data["username"]`→`data["user"]["username"]`（MeOut 嵌套）。同 `test_auth.py` 已知漂移。
  - 簇2 漏依赖夹具（2 例，`test_login_sets_cookie`/`test_login_response_includes_token_in_body`）→ **夹具缺失**：未声明 `admin_user` → 无 seed 用户 → 登录 401。补 `admin_user` 夹具参数。
  - 簇3 `/notify/` 404（2 例）→ **测试陈旧**：真实列表端点是 `/notify/channels`（需 `notify:list` 权限），根路径 `/notify/` 从不存在。改路径。
  - 簇4a trace `points`（1 例）→ **测试陈旧**：`get_trend` 返回键是 `trend`（每日桶列表），从无 `points`。改断言键。
  - 簇4c smoke 脚本结构（`test_v26_smoke` 误采集 + `test_v27_smoke` 采集中断）→ **测试结构问题**：`test_connection` 服务函数以 `test_` 前缀名导入被 pytest 误当测试收集 → 别名 `_test_connection`；`test_v27_smoke` 在 import 期硬断言未实现的 R4c 特性 → 崩溃中断整套件采集 → 加特性存在性守卫（未实现打 `[SKIP]`）。
  - `test_authorization_header_fallback`（1 例）→ **测试缺陷（端点正确，别盲目改断言）**：`TestClient` 持久化 login cookie，`/me` 自动带上 → `deps.get_current_user` 优先 cookie（不打弃用告警）→ 告警断言失败。修法：login 后 `client.cookies.clear()` 隔离纯 Authorization 头场景。**端点行为完全正确**。
- **⚠️ 待产品判定（skip+flag，未擅自实现特性）**：
  - 簇4b `test_ai_extraction_fallback` → **前瞻/未实现**：`extract_features` 无 timeout/retry/fallback 分支（超时直接 raise），config 无 `ai_timeout_seconds`/`ai_retry_attempts`/`ai_fallback_on_failure`，不返回 `fallback_used`/`extraction_progress`。跑绿=实现"DeepSeek 超时降级到本地模块提取"特性，属产品决策。已 `@pytest.mark.skip`。
  - R4c 报告模板挂接 → **前瞻/未实现**：`ReportCreate` 无 `template_id` 字段、`TestReport` 模型无该列（R4a/R4b 的模板 CRUD 已实现，R4c 挂接未做）。守卫为 `[SKIP]`。
- **产出**（全部改测试/测试结构，**零生产码改动**）：
  - `tests/test_critical_path.py` — 簇1（token/username）+ 簇4a（points→trend）
  - `tests/test_p1_security_regression.py` — 簇1（4 处 token/username）+ 簇2（2 处补夹具）+ 簇3（2 处 /channels）+ cookie jar 隔离
  - `tests/test_ai_extraction_fallback.py` — `@pytest.mark.skip`（簇4b flag）
  - `tests/test_v26_smoke.py` — `test_connection` 别名导入
  - `tests/test_v27_smoke.py` — R4c 特性存在性守卫（flag）
- **验证**：`pytest -q`（全套件，无 --ignore）→ **175 passed / 1 skipped / 0 failed / 0 error**（此前 166 passed / 10 failed / 1 error）。
- **审批**: 待用户 Review
- **耗时**: ~40min

### Batch 1 — 测试基础设施修复 (2026-07-09)
- **产出**:
  - `backend/tests/conftest.py` — `db_session` 加 `poolclass=StaticPool`；`auth_headers` 取 `data["access_token"]`
  - `backend/tests/test_auth.py` — 3 处登录响应漂移修复（`token`→`access_token`、`data.user.username`、补 `admin_user` 夹具依赖）
  - `backend/tests/test_testcase.py` — `client.delete(json=)` → `client.request("DELETE", json=)`（httpx 兼容）
  - `frontend/src/api/trace.ts` — `CoverageData` 补 `requirement_coverage_rate`
  - `frontend/src/pages/dataset/index.tsx` — `AsyncState` 用 `data` 派生空态；`Pagination` 改 `page/totalPages`
  - `frontend/src/pages/integration/index.tsx` — 去掉数组解构 `useApi`，改 `load` 回调
  - `frontend/tsconfig.json` — exclude 测试文件 + 孤儿 `TemplateManager.tsx`
- **验证**:
  - 前端 `npx tsc -b` → **exit 0**（原 17 错误归零）
  - 后端 `pytest test_auth/test_testcase/test_testplan` → **25 passed / 4 failed**（原全线失败）
- **审批**: 待用户 Review
- **耗时**: ~1h

### Batch 2 — 3 处 API 契约漂移（QA 三态化 → DEV 修复）(2026-07-09)
- **QA 三态化判定**:
  - drift1 批量路由 422 → **端点 bug**（`/{case_id}` 抢匹配 `/batch`）
  - drift2 计划执行 404 → **测试陈旧**（`/execute` 从不存在，真实端点 `/auto-execute`，无客户端引用 `/execute`）
  - drift3 删除后 GET 200 → **测试陈旧**（硬删已生效，应走 envelope 200+code=404，非软删 bug）
- **产出**:
  - `backend/app/api/v1/test_case.py` — 静态 `/batch`（含 body 类 + pydantic import）整块移到 `/{case_id}` PUT/DELETE 之前。**纯搬移，函数体零变更**（git diff 佐证）
  - `backend/tests/test_testplan.py` — `test_execute_empty_plan` 改调 `/auto-execute`；`test_delete_plan` 断言改 `status==200 && code==404`
- **验证**:
  - `pytest test_testcase.py test_testplan.py test_auth.py` → **29 passed / 0 failed**（原 4 failed 全绿）
  - 全后端套件（排除采集报错的 WIP `test_v27_smoke.py`）→ **166 passed / 10 failed**，10 处失败经逐一核验**均与本批改动无关**（登录体漂移未跟改 / notify 路径 / trace 结构 / WIP smoke），非路由重排回归
- **审批**: 待用户 Review
- **耗时**: ~40min

---

## ⚠️ 阻塞与风险

> Batch 3 清掉「第二波暴露」全部失败（9 转绿、2 skip）。Batch 4 应用户确认，将 skip 的两处未实现特性（AI 超时降级 + R4c 报告模板挂接）**已落地转绿**。当前**无功能阻塞项**，仅剩下方 alembic 历史遗留与一个可选前端增量。

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| ~~ai 提取降级特性未实现~~ | ~~P3~~ | ✅ Batch 4 已实现（config 字段 + retry + `_local_extract_modules` + 降级分支） | 已完成 | 2026-07-09 |
| ~~R4c 报告模板挂接未实现~~ | ~~P3~~ | ✅ Batch 4 已实现（model 列 + schema 字段 + create_report 挂接；迁移 0009 早已存在） | 已完成 | 2026-07-09 |
| 前端报告类型缺 `template_id` | P4（增量） | 前端 report 类型/表单未暴露 `template_id`（后端已支持）。可选，向后兼容不阻断 | 产品判定 → DEV 前端切片 | 2026-07-09 |

> 另：alembic `imported_func_count` 重复列（from-base 全链跑断）仍待处理，见 [[common-pitfalls]]「Alembic 迁移链陷阱」。

---

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| 常见陷阱 | [[common-pitfalls]] | ✅ 已更新 |
| 门禁约定 | [[agent-team-gate]] | 参考 |
