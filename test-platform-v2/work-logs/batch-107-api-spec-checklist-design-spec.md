# Batch 107 — Design Spec（接口用例生成「测试考虑点」全量固化）

> **Design (🎨)** | Date: 2026-08-06 | Status: Review

## 1. 目标契约

新增模板名（与现有 `basic/boundary/invalid/security/idempotency/extreme` 并列）：

| 模板 | 适用方法 | 每条接口生成数 | 优先级 | 说明 |
|------|---------|:---:|:---:|------|
| `smoke` | 全部 | 1 | P0 | 以真实样本/语义入参为起点，断言完成业务功能（响应结构+业务码） |
| `scenario` | 全部 | 1 | P1 | 多接口串联状态转变；无关联信息时生成「场景测试建议」待关联用例 |
| `extra_param` | 全部 | 1 | P1 | body 增加不存在参数，断言 4xx 或忽略，不得 5xx |
| `security_ext` | 全部 | 2–3 | P1 | 越权（弱/无效 token）、CSRF（写接口）、HTTPS/签名/加密检查 |
| `performance_low` | 全部 | 2–3 | P2/P3 | 并发/吞吐/资源监控建议（低优先级，非阻塞断言） |
| `data_test` | 全部 | 1–2 | P2 | 数据库入库/字段类型长度一致性（DB 检查断言） |
| `stability` | 全部 | 1–2 | P2 | 限流/熔断/降级（按服务策略验证） |
| `compatibility` | 全部 | 1–2 | P2 | 入参/返回值/老功能兼容 |
| `monitoring` | 全部 | 1–2 | P2 | 性能监控 qps/rt + 业务监控错误码/指标 |

## 2. 规则生成器实现（`backend/app/services/api_case_generation_service.py`）

### 2.1 新函数

- `_build_smoke_cases(ep, real)` → `list[dict]`：复用真实样本 body；断言 `status_code 2xx` + `response_structure`（业务码/记录数/核心字段，若 real 含 response 结构）+ `response_time < 5000`。
- `_build_scenario_cases(ep, real)` → `list[dict]`：单条「场景测试建议」用例；若 `real` 或 endpoint tags 含 `related_endpoints`/`assertion_design_hints` 则引用之，否则标注「依赖接口关联信息（接口串联状态转变），关联后补全」。
- `_build_extra_param_cases(ep, real)` → `list[dict]`：取 body 的副本，添加 `__unknown_extra_field__`（若 real body 存在则追加到末尾）；断言 4xx 或 2xx（忽略未知字段），不得 5xx。
- `_build_security_ext_cases(ep)` → `list[dict]`：
  - 写方法：CSRF 用例（无 CSRF 头/伪造 Origin，断言 4xx 或安全拒绝，不得 5xx）。
  - 全部：越权用例（弱 token `invalid-token`，断言 401/403 或业务拒绝）；HTTPS/签名检查用例（断言 `scheme=https` + 响应不泄露明文敏感字段）。
- `_build_performance_low_cases(ep)` → `list[dict]`：并发（N=10 同参数并发不 5xx）、吞吐/资源监控建议（qps/rt/CPU/内存观察）各 1 条，P2/P3。
- `_build_data_test_cases(ep)` → `list[dict]`：DB 入库校验用例（执行后查库记录存在/字段一致），断言类型 `db_check`；字段类型/长度与页面输入一致性检查建议。
- `_build_stability_cases(ep)` → `list[dict]`：限流（高频请求触发限流时不 5xx 且有策略响应）、熔断/降级（服务降级提示不 5xx）。
- `_build_compatibility_cases(ep)` → `list[dict]`：入参兼容（旧参数集请求不破坏）、返回值兼容（响应字段按序新增）、老功能兼容。
- `_build_monitoring_cases(ep)` → `list[dict]`：监控指标用例（qps/rt/错误码/业务指标上报可见）。

### 2.2 主流程扩展（`generate_cases_from_endpoint`）

```python
default_templates = ["basic", "boundary", "invalid", "security", "idempotency", "extreme",
                     "smoke", "scenario", "extra_param", "security_ext", "performance_low",
                     "data_test", "stability", "compatibility", "monitoring"]
```

- `templates is None` 时使用上述全量默认集（与前端默认一致）。
- 每个新模板独立 `if "xxx" in templates` 分支，追加到 cases。
- 数量上限保护维持 `_MAX_CASES_PER_ENDPOINT = 200`。

### 2.3 真实样本响应结构断言（`generate_cases_from_real_sample`）

- 读取 `real_sample`：`response_status`、`response_envelope_keys`、`data_keys`、`record_count`、`first_record_fields`、`assertion_design_hints`。
- 正向基线用例断言升级：`status_code 2xx` + `response_structure`（如 `{"path":"status","expected":"0","assert":"eq"}`、`{"path":"data.records","assert":"is_array"}`、`{"path":"data.total","assert":"gte","expected":0}`）+ 核心字段非空（`first_record_fields[:5]`）。
- 新增「返回值结构校验」正向用例（`scenario="response_structure"`）：按 hints 生成断言（业务码=0、records≤size、排序规则、language 过滤、核心字段非空）。
- 分页/排序/组合用例的断言同时补充对应响应结构断言（如 page 超总页数 → records 空数组或 total=0）。

## 3. AI 提示词（`backend/app/services/ai_service.py`）

- `_load_skill_context_for(kind)`：`kind="api"` 时加载 `api-checklist.md` + `接口测试考虑点.md` + `SKILL.md`（文件缺失则降级并记录日志）。
- `_build_system_prompt` 的 api_cases 字段说明升级：
  - `api_assertions`：状态码 + 响应结构（业务码/记录数/核心字段）+ 业务规则。
  - `kind_rules` 增加：接口用例须覆盖「测试考虑点」（冒烟/场景串联/健壮性合法非法/安全加密越权 CSRF/性能低优先级/数据入库/稳定性/兼容性/监控）且数据真实贴合业务语义。

## 4. 文档落盘（`tests/test-case-standards/`）

- `接口测试考虑点.md`：按 XMind 树转写（业务功能测试→冒烟/场景；健壮性测试→合法/非法；安全测试→加密/SQL/XSS 暂不/越权/CSRF；性能测试→响应/吞吐/并发/资源；数据测试→基本/专业化），101 节点全量。
- `CLAUDE.md` / `api-checklist.md`：增加「接口测试考虑点」引用。
- `.agents/skills/test-case-design/api-checklist.md`：增加「测试考虑点」速查段（冒烟/场景/安全扩展/数据/性能低优先级）。

## 5. Schema 与前端

- `backend/app/schemas/api_asset.py`：`GenerateApiCasesRequest`/`BatchGenerateRequest` 默认 `templates` 与生成器默认集一致（全量 15 项）。
- `frontend/src/pages/apitest/components/AssetTab.tsx`：`handleGenerate` 默认数组加入 9 个新模板名。

## 6. 单测（`backend/tests/test_api_case_spec_checklist.py`）

- 每个新模板在对应 method/schema 下生成条数正确、断言类型正确。
- 真实样本响应结构断言：list_visible 样本生成结果含 `response_structure`/`db_check` 等业务断言（非仅状态码）。
- 默认模板集包含全部 15 项；上限保护生效。
- 现有 `test_api_case_real_sample.py`、`test_apitest_generation.py` 不回归。

## 7. 环境与执行

- 本批为后端行为扩展 + 规范文档，无数据库 Schema 变更 → **无需 Alembic 迁移**。
- 验证使用 worktree 本地 pytest + 生成器实测（真实样本文件来自 `work-logs/evidence/batch-103/`）。
