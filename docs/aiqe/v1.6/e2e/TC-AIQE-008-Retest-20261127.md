# TC-AIQE-008 修复回归复测（2026-11-27）

## 输入
- 权威用例/问题表：`未来娃屿V5.0_用例整理与问题登记_20261117 的手工验收(1)(1)(1)(1)(1).xlsx`
- `03-待复测（26条）`：甲方反馈已解决、待复测
- 首个复测项：`WWY-V5-001`；另选已修复项：`WWY-V5-006`

## WWY-V5-001 复测结果：FAIL（仍未修复）
- 账号：`tester-operator`（运营）
- 请求：`POST https://xinyuwadao.com/prod-api/system/device`，空体 `{}`
- 实际：HTTP 200，body `code=500`，`msg=设备类型不能为空`
- 期望：`403`（运营对设备只读，不应进入新增逻辑）
- 结论：鉴权已通过、进入业务校验；**修复未生效/未部署**

## 另选已修复缺陷：WWY-V5-006（PASS）
- 用例：`TC-ADM-01-D` 后台登录：保存与刷新后状态持久化
- 原失败：勾选“记住账号”后刷新，输入框空、localStorage 无记忆项
- 复测：`tester-operator` 登录页勾选记住账号 → 返回登录页刷新
  - 用户名输入框自动回填 `tester-operator`
  - `localStorage.username=tester-operator`、`rememberMe=true`
- 结论：**修复回归通过**
- 证据：`docs/aiqe/v1.6/evidence/product/TC-AIQE-008/remember-account.json` + 截图
- AIQE Run：`bbd4aa79`，节点 PASSED

## 补充：运营/店员设备删除 403 复测
- 店员 `tester-clerk`：`DELETE /prod-api/system/device/0` → `code=403`（符合新矩阵）
- 运营 `tester-operator`：同一请求 → `code=500`（仍未按 403 拦截）
- 运营 `POST/PUT /system/device` 在 V5.0 允许（V5 明确“门店设备可新增和修改”），空体 500 属校验错误码问题，不是越权

## 结论
- TC-AIQE-008 用 `WWY-V5-006` 完成“修复后点击回归”，产品 TC 状态 **PASS**。
- `WWY-V5-001` 仍作为未修复缺陷保留，待 V5 权限口径确认后再处理。

## 证据
- `docs/aiqe/v1.6/evidence/product/TC-AIQE-008/remember-account.json`
- `docs/aiqe/v1.6/evidence/product/TC-AIQE-008/remember-account.png`
- 复测命令与响应见 `work-logs/aiqe-v16-1-audit-closure-20261124.md` 第 33 节。
