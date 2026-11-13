# npm audit 新公告 triage：basic-ftp（2026-11-13）

## 1. 事实

`npm audit ratchet` 在 PR #569 上失败，新增 2 条公告：

```
basic-ftp|1246355
basic-ftp|1246367
```

依赖路径（纯开发依赖）：

```
@lhci/cli@0.15.1 → proxy-agent@6.5.0 → pac-proxy-agent@7.2.0
  → get-uri@6.0.5 → basic-ftp@5.3.1
```

## 2. 验证过的修复路径

| 方案 | 结果 |
|------|------|
| 升级 `@lhci/cli` 0.15.1 → 0.16.1 | ❌ 仍解析 `get-uri@8.0.1 → basic-ftp@5.3.1`，两条公告仍在（总公告 68→54，但不解决 basic-ftp） |
| 升级 `basic-ftp` 5.x | ❌ 无 5.3.2；6.x 为大版本，`get-uri` 未声明兼容 |
| `overrides` 强制 basic-ftp@6 | ⚠️ 可能破坏 `get-uri` FTP 分支（无上游验证），不做未验证覆盖 |

## 3. 决策

- 该依赖仅用于 Lighthouse CI 的代理解析（FTP 场景不会在 CI 触发），**不进入生产依赖**；
- 按仓库 ratchet 的既定机制执行 `--update` 登记（68 → 69 条），并保留本次 triage 证据；
- **生产依赖审计仍为零**（`npm audit --omit=dev --audit-level=high` 独立门禁不变）；
- 后续（M9 batch-344 / M10 349）：跟踪 `get-uri`/`proxy-agent` 上游升级；若仍无修复，评估替换 `@lhci/cli` 或移除 FTP 传输依赖，而不是永久保留豁免。

## 4. 复现

```bash
cd test-platform-v2/frontend
node ../../scripts/ci/npm_audit_ratchet.mjs            # new=0 removed=0
node ../../scripts/ci/npm_audit_ratchet.mjs --update   # 重新登记（仅 triage 后）
```
