# TC-AIQE-008 缺陷回归复测记录（2026-11-27，2026-11-28 按 FIX-008 拆分）

> **结论先行：TC-AIQE-008 的产品级验收仍未完成（NOT_PROVEN）。**
> 原缺陷 `WWY-V5-001` 保持 **FAIL / OPEN**；`WWY-V5-006` 只是另一条用例的单用例
> 点击复核，不构成 TC-AIQE-008 的产品级通过证据，也不能关闭 `WWY-V5-001`。

## 1. 输入

- 权威用例/问题表：`未来娃屿V5.0_用例整理与问题登记_20261117 的手工验收(1)(1)(1)(1)(1).xlsx`
  - `03-待复测（26条）`：甲方反馈已解决、待复测
- 首个复测项：`WWY-V5-001`；另选已修复项：`WWY-V5-006`
- 账号：只记录 Secret 名称，取值由 CI Secret / Vault 注入
  - 运营：`FUTUREWAYU_TEST_USERNAME` / `FUTUREWAYU_TEST_PASSWORD`
  - 店员：`FUTUREWAYU_TEST_CLERK_USERNAME`

## 2. `WWY-V5-001` 复测：FAIL / OPEN（仍未修复）

- 请求：`POST https://xinyuwadao.com/prod-api/system/device`，空体 `{}`
- 实际：HTTP 200，body `code=500`，`msg=设备类型不能为空`
- 期望：`403`（运营对设备只读，不应进入新增逻辑）
- 结论：鉴权已通过、进入业务校验；**修复未生效/未部署**
- 正式回归证据：**无**（没有固定 `fixed_commit_sha`、Mandatory Scope Snapshot、
  Regression Run、Mandatory Case Results、Comparison Snapshot）
- 缺陷状态：**FAIL / OPEN**，不得因其他用例通过而关闭

## 3. `WWY-V5-006` 单用例点击复核：UI 观察通过，状态 NOT_PROVEN

- 用例：`TC-ADM-01-D` 后台登录：保存与刷新后状态持久化
- 原失败：勾选“记住账号”后刷新，输入框空、localStorage 无记忆项
- 复测（`scripts/aiqe/per_tc/futurewayu_remember_account.py`）：
  运营账号登录页勾选记住账号 → 返回登录页刷新
  - 用户名输入框自动回填
  - `localStorage.username` 与会话账号一致、`rememberMe=true`
- UI 观察：通过（仅此一条用例）
- 用例状态：**NOT_PROVEN**
  - 原因：该脚本直接驱动 Playwright 检查 localStorage，**不经过正式 Defect Regression
    API**，没有 fixed commit SHA、Mandatory Scope Snapshot、Mandatory Case Results 与
    Comparison Snapshot（手册 §9.4.9）
  - 输出字段：`defect_id=WWY-V5-006`、`case_id=TC-ADM-01-D`、`status=NOT_PROVEN`、
    `product_tc_status=NOT_PROVEN`、`defect_state_unchanged=["WWY-V5-001"]`
- 证据：`docs/aiqe/v1.6/evidence/product/TC-AIQE-008/remember-account.json` + 截图
  - 注意：仓库现存的 `remember-account.json` 是旧版脚本产物（`status=PASS`、并把它当作
    TC 级通过）。按 FIX-008 该结论作废；需要在具备 Secret 的环境中用新脚本重跑覆盖，
    或直接用 `defect_regression_runner.py` 走正式回归链路。
- AIQE Run `bbd4aa79` 属旧记录，只证明平台链路有执行记录，不构成本用例的产品级通过证据。

## 4. 补充：运营/店员设备删除 403 复测

- 店员（`FUTUREWAYU_TEST_CLERK_USERNAME`）：`DELETE /prod-api/system/device/0` → `code=403`（符合新矩阵）
- 运营（`FUTUREWAYU_TEST_USERNAME`）：同一请求 → `code=500`（仍未按 403 拦截）
- 运营 `POST/PUT /system/device` 在 V5.0 允许（V5 明确“门店设备可新增和修改”），空体 500 属校验错误码问题，不是越权

## 5. 两条用例的分开记录

| 缺陷/用例 | 用例号 | 状态 | 证据 | 是否可关闭 |
|---|---|---|---|---|
| `WWY-V5-001` | `TC-ADM-06-N` | **FAIL / OPEN** | 本文件 §2；无正式回归 Run | 否，必须自身正式回归 PASS |
| `WWY-V5-006` | `TC-ADM-01-D` | **NOT_PROVEN**（UI 观察通过） | `remember-account.json`（待重跑覆盖） | 否，缺正式回归链路证据 |

## 6. 正式回归入口

```powershell
python scripts/aiqe/per_tc/defect_regression_runner.py `
  --api-base <平台 API 基址> --project-id <项目 ID> --defect-id <缺陷主键> `
  --fixed-commit-sha <40 位修复提交> --scope-snapshot <scope-json> `
  --idempotency-key <唯一幂等键> --case-results <mandatory case 结果> `
  --output <回归结果 JSON>
```

- 缺参数 / API 不可达 → `BLOCKED`；缺 fixed SHA、Mandatory Scope 全覆盖、Mandatory Case
  结果或 Comparison Snapshot → `NOT_PROVEN`；只有全部满足且原缺陷自己的回归 Run 通过，
  才可能 `PASS` 并把缺陷更新为修复验证完成（需审计事件）。
- 另一条用例（例如 `WWY-V5-006`）PASS 不会改变 `WWY-V5-001` 的状态。

## 7. 未完成项

| 项 | owner | 解除条件 |
|---|---|---|
| `WWY-V5-001` 正式回归 | QA + 缺陷负责人 | 提供修复提交固定 SHA + scope snapshot + case results，并在可访问的平台上调用正式 Regression API |
| `WWY-V5-006` 单用例证据重跑 | QA | 注入 `FUTUREWAYU_TEST_USERNAME` / `FUTUREWAYU_TEST_PASSWORD` 后重跑新脚本，覆盖旧 JSON |
| 历史截图复检/重拍 | QA | `docs/aiqe/v1.6/evidence/product/TC-AIQE-008/remember-account.png` 等旧截图可能包含账号明文；新脚本已对输入框做文本遮蔽，旧图需重拍或脱敏后替换 |
| 矩阵/产品结果状态修正 | FIX-003 owner | `requirements.yaml` 与 `product-results.json` 中 TC-AIQE-008 的产品状态需要与本文档一致，不再引用旧的 `remember-account.json` 作为通过证据 |
