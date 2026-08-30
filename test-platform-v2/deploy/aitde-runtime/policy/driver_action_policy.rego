# AITDE V3.4 — OPA 策略样例（drop-in 可选）
#
# 可选基础设施：若启用 OPA，可把此 Rego 挂到 Policy Gateway 的 OPA Provider。
# 当前实现为自研 PolicyGateway（app/modules/aitde/workflow/policy.py），本文件
# 用于与 OPA 对齐/审计；两边规则必须保持一致（V34-010 无绕过）。

package cameltv.aitde.driver_action

# 输入约定与 V3.4 §6 一致：
#   { "actor","project_id","environment_id","network_zone","driver","action","target" }

write_actions = {"fixture_update", "db_exec", "create", "update", "delete", "insert", "grant"}
database = {"database"}

# Production 只读：任何写动作 DENY
deny {
  input.network_zone == "PROD_RO"
  input.action in write_actions
}

# Office 不写测试数据
deny {
  input.network_zone == "OFFICE"
  input.action in write_actions
}

# 危险 DB 写需审批（TEST 等非只读区），production 已由上面 deny 覆盖
require_approval {
  input.driver in database
  input.action in {"fixture_update", "db_exec"}
  not input.network_zone == "PROD_RO"
  not input.network_zone == "OFFICE"
}

# 汇总：deny > require_approval > allow
decision := "DENY" { deny }
decision := "REQUIRE_APPROVAL" { not deny; require_approval }
decision := "ALLOW" { not deny; not require_approval }
