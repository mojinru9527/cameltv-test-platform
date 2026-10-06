#!/bin/bash
# C273-2：撤销公开仓库中泄漏的平台 Token（sports-ci）。
# 只把 enabled 置 false（可逆），不删除行——保留审计痕迹。
P() { docker exec cameltv-tp-production-postgres-1 psql -U cameltv -d cameltv_production -X -A -F'|' -c "$1"; }

echo "===== BEFORE ====="
P "select id, name, token_prefix, enabled, created_at, last_used_at from api_token order by id;"

echo
echo "===== 撤销 id=1 (sports-ci, 泄漏值已在公开仓库) ====="
# 守卫用 id + name，不用 token_prefix：token_prefix 本身也是凭据的一部分，
# 写进仓库等于把凭据片段又留一份。id+name 的定位强度等价且不含凭据材料。
P "update api_token set enabled = false where id = 1 and name = 'sports-ci' and enabled = true;"

echo
echo "===== AFTER ====="
P "select id, name, token_prefix, enabled, created_at, last_used_at from api_token order by id;"

echo
echo "===== 复核：仍 enabled 且命中该行特征的行数（必须为 0）====="
P "select count(*) as leaked_and_still_enabled from api_token where enabled = true and id = 1 and name = 'sports-ci';"
