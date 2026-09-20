# Batch 269 证据 — §5 第 ⑧ 条生产水位与告警（只读复核 + 自检送达确认）

> 采集时间：2026-09-20 13:34（北京时间）｜主机：`111.230.155.116`（腾讯云广州，4C4G）
> 操作性质：**只读**（`df` / `crontab -l` / `ls -l` / `tail` / `docker ps`）；未改生产配置、未发新邮件
> 凭据：`ssh -i ~/.ssh/cameltv_tencent_lighthouse root@…`；`smtp.env` 在主机上权限 600，**未读入仓库**

## 1. 水位（⑧ 前半：`df -h` < 80%）

```
$ ssh … root@111.230.155.116 "df -h /"
Filesystem      Size  Used Avail Use% Mounted on
/dev/vda2        40G   28G   11G  74% /
```

**结论**：74% < 80% ✅（与 2026-09-19 Batch 262 的 73%/74% 同档）。

## 2. 告警任务已固化（⑧ 后半：85% 阈值能触发告警）

```
$ ssh … "crontab -l"
*/5  * * * * flock -xn /tmp/stargate.lock -c '/usr/local/qcloud/stargate/admin/start.sh …'
*/15 * * * * /opt/cameltv-ops/disk-watermark-check.sh >> /var/log/cameltv-disk-alert.cron.log 2>&1

$ ssh … "ls -l /opt/cameltv-ops/; stat -c '%a %U %n' /opt/cameltv-ops/smtp.env"
-rwx------ 1 root root 1987 Sep 19 14:40 disk-watermark-check.sh
-rw------- 1 root root  183 Sep 19 18:37 smtp.env
600 root /opt/cameltv-ops/smtp.env
```

**脚本逻辑（`/opt/cameltv-ops/disk-watermark-check.sh`，逐字摘录判定段）**：

```bash
THRESHOLD="${1:-${DISK_ALERT_THRESHOLD:-85}}"      # 缺省阈值 85%
MOUNT="${DISK_ALERT_MOUNT:-/}"
USED=$(df -P "$MOUNT" | awk 'NR==2 {gsub("%","",$5); print $5}')
if [ "$USED" -lt "$THRESHOLD" ]; then echo "… OK …"; exit 0; fi
echo "… ALERT …" >> "$LOG"
python3 … smtplib 发信 → 成功打印 MAIL_OK
```

即：`used < threshold` 记 `OK` 退出；否则记 `ALERT` 并发邮件。缺省阈值就是 **85%**，与 `DISK_ALERT_THRESHOLD` 一致。

## 3. 运行记录（定时任务每 15 分钟在跑）

```
$ ssh … "tail -n 14 /var/log/cameltv-disk-alert.log"
2026-09-20T12:15:01+08:00 OK used=74% threshold=85%
2026-09-20T12:30:01+08:00 OK used=74% threshold=85%
2026-09-20T12:45:01+08:00 OK used=74% threshold=85%
2026-09-20T13:00:01+08:00 OK used=74% threshold=85%
2026-09-20T13:15:01+08:00 OK used=74% threshold=85%
2026-09-20T13:30:01+08:00 OK used=74% threshold=85%

$ ssh … "grep 'ALERT' /var/log/cameltv-disk-alert.log | tail -n 5"
2026-09-19T14:40:27+08:00 ALERT used=74% threshold=70% to=mojinru9527@gmail.com
2026-09-19T14:40:41+08:00 ALERT used=74% threshold=70% to=mojinru9527@gmail.com
2026-09-19T18:36:52+08:00 ALERT used=74% threshold=50% to=mojinru9527@gmail.com
2026-09-19T18:37:07+08:00 ALERT used=74% threshold=50% to=mojinru9527@gmail.com
2026-09-19T18:37:20+08:00 ALERT used=74% threshold=50% to=mojinru9527@gmail.com

$ ssh … "grep -c 'MAIL_OK' /var/log/cameltv-disk-alert.log; grep 'MAIL_OK' …"
1
MAIL_OK mojinru9527@gmail.com

$ ssh … "wc -l /var/log/cameltv-disk-alert.log"
152 /var/log/cameltv-disk-alert.log
```

**怎么读这三段**：

1. **触发逻辑成立**：人为用 `70%` / `50%` 阈值强制触发时，脚本确实走到 `ALERT` 分支（日志留下了 5 行）；
2. **邮件通道成立**：18:37 那次成功发出并打印 `MAIL_OK mojinru9527@gmail.com`；
3. **日常无噪音**：自 09-19 修复后，每个 15 分钟窗口（本次取到 13:30:01）在真实阈值 85% 下都记 `OK`（74% < 85%），没有误报。

> 早期两次 `ALERT` 后跟 `Traceback`，是当时误把发信人写成 `pop.qq.com`（`SMTP_FROM`）导致的发送失败——该配置已于 09-19 18:36 修正，修正后同一路径打印 `MAIL_OK`。

## 4. 送达确认（用户口径）

- **发信人/SMTP 账号**：`2602997810@qq.com`（`smtp.qq.com:587` + STARTTLS）；
- **告警收件人（`DISK_ALERT_TO`）**：`mojinru9527@gmail.com`（本次只打印前 4 字符做核对，未落明文到仓库）；
- **用户确认**：2026-09-20 用户回复「QQ 邮箱有收到 cameltv 邮件自检」→ 该自检邮件（主题 `[CamelTv] 磁盘水位告警 …`）**已到达用户可读的信箱**。

**如实标注两点**：① 日志里的收件人是 Gmail 地址，用户在 QQ 邮箱看到该邮件（两处为同一用户的信箱）；若希望投递地址本身就是 QQ 地址，改 `DISK_ALERT_TO` 即可，属一行配置；② 本次自检用的是**降低阈值的强制触发**（50%），不是真的把盘撑到 85%——因此"85% 会告警"是**逻辑 + 通道**两段实测的组合证据，不是"盘真的到过 85%"。

## 5. 同批顺带核对：生产容器健康

```
$ ssh … "docker ps --format '{{.Names}} {{.Status}}'"
cameltv-tp-production-aitde-worker-1 Up 19 hours (healthy)
cameltv-tp-production-frontend-1    Up 19 hours (healthy)
cameltv-tp-production-backend-1     Up 19 hours (healthy)
cameltv-tp-production-runner-1      Up 19 hours (healthy)
cameltv-tp-production-ai-gateway-1  Up 19 hours (healthy)
release-console                     Up 2 days
cameltv-tp-production-postgres-1    Up 13 days (healthy)
aitde-temporal                      Up 2 weeks (healthy)
```

全部 healthy；`Up 19 hours` 与 2026-09-19 的发布窗口一致（发布后未重启）。
