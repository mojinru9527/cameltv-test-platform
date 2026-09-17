#!/usr/bin/env bash
# Batch 256 — C243-1 S1/S2 真实运行探针
#
# 在 read_only rootfs + tmpfs 白名单 + cap_drop ALL + no-new-privileges + 非 root
# 的 runner 容器里，验证：
#   1) 镜像路径写入被拒（EROFS）
#   2) /tmp 与持久卷可写
#   3) `npx playwright test`（平台真实执行路径）仍能启动浏览器并通过
#
# 用法（由 QA 报告记录完整 docker run 命令）：
#   bash /probe.sh
set -uo pipefail

OUT=/app/storage/ui-runs/probe
SPEC_DIR=/app/tests/playwright/specs/generated
mkdir -p "$OUT" "$SPEC_DIR"

echo "PROBE_START=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "UID=$(id -u) USER=$(id -un)"
echo "ROOTFS=$(awk '$2=="/"{print $3" "$4}' /proc/mounts | cut -c1-60)"
echo "STORAGE_MOUNT=$(awk '$2=="/app/storage"{print $3" "$4}' /proc/mounts | cut -c1-60)"

# 1) 镜像路径必须不可写
if (echo x > /app/ro-probe.txt) 2>/tmp/ro.err; then
  echo "APP_WRITE=UNEXPECTED_OK"
else
  echo "APP_WRITE=blocked:$(tr -d '\n' < /tmp/ro.err)"
fi

# 2) 白名单可写点
echo x > /tmp/rw-probe.txt && echo "TMP_WRITE=ok"
echo x > "$OUT/rw-probe.txt" && echo "STORAGE_WRITE=ok"
echo x > "$SPEC_DIR/rw-probe.txt" && echo "GENERATED_SPEC_WRITE=ok"

# 3) 真实 Playwright 执行路径
cat > "$SPEC_DIR/batch256-probe.spec.ts" <<'SPEC'
import { test, expect } from '@playwright/test';

test('batch256 read-only rootfs smoke', async ({ page }) => {
  await page.setContent(
    '<html><head><title>batch256</title></head><body><h1 id="h">ok</h1></body></html>',
  );
  await expect(page.locator('#h')).toHaveText('ok');
});
SPEC

cd /app/tests/playwright
npx playwright test specs/generated/batch256-probe.spec.ts \
  --project chromium --reporter json --output "$OUT/artifacts" \
  > "$OUT/report.json" 2>"$OUT/stderr.log"
echo "PLAYWRIGHT_EXIT=$?"

python - "$OUT/report.json" <<'PY'
import json
import sys

try:
    report = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as exc:  # noqa: BLE001 - probe must report, not raise
    print(f"REPORT_PARSE=failed:{exc}")
    sys.exit(0)

stats = report.get("stats", {})
print(
    "PLAYWRIGHT_STATS="
    f"expected={stats.get('expected')} unexpected={stats.get('unexpected')} "
    f"flaky={stats.get('flaky')} skipped={stats.get('skipped')}"
)
titles = [
    (suite.get("title"), case.get("title"), case.get("status"))
    for suite in report.get("suites", [])
    for case in suite.get("specs", [])
]
print(f"PLAYWRIGHT_SPECS={titles}")
PY

echo "PROBE_END=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
