#!/usr/bin/env bash
# 复刻 ai-delivery-policy.yml 的凭据扫描步骤，验证「能拦住真凭据 / 不误报普通词」。
set -uo pipefail

CREDENTIAL_PATTERNS='ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|BEGIN (RSA|OPENSSH|EC|PGP) PRIVATE KEY|(^|[^A-Za-z0-9])sk-[A-Za-z0-9]{20,}|(^|[^A-Za-z0-9])tpat_[A-Za-z0-9_-]{16,}|(^|[^A-Za-z0-9])agt_[A-Za-z0-9_-]{16,}'
PLACEHOLDER_ALLOWLIST='(sk-(test|xxx|your|example|placeholder|redacted)|tpat_XXXXXXXX|agt_XXXXXXXX|<REDACTED>|CHANGE_?ME|change-me)'

check() {
  local label="$1" expect="$2" line="$3"
  local added_lines="+${line}"
  local got="pass"
  if printf '%s\n' "$added_lines" \
      | grep -vE "$PLACEHOLDER_ALLOWLIST" \
      | grep -qE "$CREDENTIAL_PATTERNS"; then
    got="block"
  fi
  if [ "$got" = "$expect" ]; then
    printf 'OK   %-46s expect=%-5s got=%s\n' "$label" "$expect" "$got"
    return 0
  fi
  printf 'FAIL %-46s expect=%-5s got=%s\n' "$label" "$expect" "$got"
  return 1
}

fails=0

# ── 测试样本必须**运行时拼装**，绝不写字面量 ──
# 两条硬理由：
#   ① 写下真实泄漏物的明文 = 把刚清掉的东西又 commit 回公开仓库；
#   ② 本文件的这些行本身就是「新增行」，会被本仓库自己的凭据门禁
#      （ai-delivery-policy.yml）判为凭据 → **本 PR 被自己的门禁拦下**。
# 因此这里用合成样本：前缀靠 printf 拼接断开（源码里不存在连续的 `sk-`/`tpat_`/`agt_`），
# 样本体也是纯合成的，不使用任何真实 Key 的片段。测试效力不变。
SK_SAMPLE="$(printf 's''k-%s' '0123456789abcdefghijklmnopqrstuv')"
TPAT_SAMPLE="$(printf 'tp''at_%s' 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefg')"
AGT_SAMPLE="$(printf 'ag''t_%s' 'ZYXWVUTSRQPONMLKJIHGFEDCBA9876543210zyxwv')"
GHP_SAMPLE="$(printf 'gh''p_%s' 'abcdefghijklmnopqrstuvwxyz0123456789')"
AKIA_SAMPLE="$(printf 'AK''IA%s' 'IOSFODNN7EXAMPLE')"
PEM_SAMPLE="$(printf -- '-----BEGIN %s PRIVATE KEY-----' 'OPENSSH')"

# ── 真实凭据形态：必须拦下 ──
check "platform API token (tpat_)"          block "  \"ci_token\": \"${TPAT_SAMPLE}\"," || fails=$((fails+1))
check "deepseek sk- key"                    block "AI_API_KEY=${SK_SAMPLE}" || fails=$((fails+1))
check "ai agent token agt_"                 block "TOKEN=${AGT_SAMPLE}" || fails=$((fails+1))
check "github classic pat"                  block "token: ${GHP_SAMPLE}" || fails=$((fails+1))
check "aws access key id"                   block "AWS_ACCESS_KEY_ID=${AKIA_SAMPLE}" || fails=$((fails+1))
check "openssh private key header"          block "${PEM_SAMPLE}" || fails=$((fails+1))

# ── 普通文本 / 占位符：不得误报 ──
check "disk-watermark-check.sh"            pass  'cron: */15 * * * * /opt/cameltv-ops/disk-watermark-check.sh' || fails=$((fails+1))
check "risk-queue-workers-describe"        pass  'const x = "risk-queue-workers-describe-more"' || fails=$((fails+1))
check "mask-image-linear-from-pos"         pass  '"mask-image-linear-from-pos":[{mask:["linear"]}]' || fails=$((fails+1))
check "task-icon-arrow (minified js)"      pass  'sk-task-icon-arrow-forward,X=()=>[w,"auto",D,z]' || fails=$((fails+1))
check "placeholder tpat_replace_me"        pass  'PLATFORM_API_TOKEN=tpat_replace_me' || fails=$((fails+1))
check "fixture tpat_test_on"               pass  "  token_prefix: 'tpat_test_on'," || fails=$((fails+1))
check "docs tpat_xxxxxxxx"                 pass  'Authorization: Bearer tpat_xxxxxxxx' || fails=$((fails+1))
check "sk-test fixture"                    pass  'api_key="sk-test-1234567890abcdef"' || fails=$((fails+1))
check "SECRET_KEY change-me placeholder"   pass  'SECRET_KEY=change-me-production-secret-key' || fails=$((fails+1))
check "redacted marker"                    pass  '  "ci_token": "<REDACTED>",' || fails=$((fails+1))

echo
if [ "$fails" -eq 0 ]; then
  echo "ALL CHECKS PASSED"
  exit 0
fi
echo "$fails CHECK(S) FAILED"
exit 1
