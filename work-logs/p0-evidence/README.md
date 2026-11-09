# P0 证据目录（AIQE M0 Gate）

> 由 `scripts/ci/check-p0-ready.ps1` 读取：`status=pass` 且 `checked_at` 在 30 天内才通过。
> 本目录只放**可复核**的真实证据；未完成的条目不放 `pass`。

## 当前状态（2026-11-09 22:30 +08:00）

| P0 | 状态 | 证据 | 剩余 |
|----|------|------|------|
| P0-1 Key 轮换 | ❌ BLOCKED | `P0-1-BLOCKED.md`（生产 3 条 provider 全 401，本地 Key 也 401） | 需要有效 DeepSeek Key 或控制台账号 |
| P0-2 备份 + DROP 守卫 | ✅ pass | `P0-2-backup-restore.json` + `raw/p0-2-backup-drill-20261109.log.txt` | 生产尚未执行 20261007 的 104 表 DROP（需发布窗口确认） |
| P0-3 磁盘 | 🟡 in_progress | `P0-3-disk-watermark.json` + `raw/p0-3-cleanup-20261109.log.txt` | 87%→67%，48h 观察至 2026-11-11 14:13Z |
| P0-4 /uitest 剥离 | 🟡 PARTIAL | `P0-4-BLOCKED.md`；277b-1 契约 PR #502 | 迁 lanhu/xhr/playground 浏览器 + 真机验收 + Dockerfile + 发布 |

## 校验

```powershell
pwsh scripts/ci/check-p0-ready.ps1
pwsh scripts/ci/check-p0-ready.ps1 -SelfTest   # 守卫自检
```

## P0-2 细节（本次生产演练）

- 库：`cameltv_production`（681 MB）
- dump：`/root/backups/cameltv_production-20261109-221328.dump`（168 MB）
- sha256：`8f100def15b06cb7e53e4a2a1e35ff90bba065005c19bfd4afd2c43871f962ee`
- 恢复：scratch DB `cameltv_production_restore_drill_20261109_221328`，`pg_restore rc=0`，10 张抽样表行数一致，之后 DROP
- 生产 alembic：`20260927_ai_guard_and_job_attempts`

## P0-3 细节

- 清理：3 组旧 release 镜像（20260919/24/1007，共 12 个 tag）+ `journalctl --vacuum-size=100M`
- 结果：87%（33G used / 5.1G avail）→ 67%（25G used / 13G avail；演练 dump 后 69%）
- 监控：`/etc/cron.d/p0-3-watermark` 每小时写 `/root/p0-3-watermark.log.txt`

## 完成 P0-1 的命令骨架（拿到新 Key 后）

```python
# 容器内
from app.core.cipher import encrypt_value
# UPDATE ai_provider SET api_key_encrypted=encrypt_value('<new-key>') WHERE id=<id>;
```
然后重启 backend，真实调用一次并把 `model_usage_ledger` 新行写进证据。
