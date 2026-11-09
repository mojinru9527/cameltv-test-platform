# Batch 277b-2 — 运维证据：Leader Verdict

> **部门**：🎯 Leader
> **日期**：2026-11-09
> **输入**：PRD-lite + QA + 生产日志

---

## 1. 判决

# ✅ APPROVED（证据批次）

**理由**：

- P0-2 的备份恢复**真实执行**：681MB 库 dump 168MB、sha256 记录、scratch 恢复 10 表行数一致、scratch 已删；
- P0-3 清理**真实执行**：87% → 67%，保留 `:main` 与运行中镜像，仅删旧 release tag + journal；
- P0-3 证据保持 `in_progress`，**没有把 48h 观察伪造为 pass**；
- P0-1 / P0-4 的阻塞有实测依据（401 状态码、生产 alembic 版本、浏览器使用面）；
- 明确声明未部署、未 upgrade、未改 env、未删业务数据。

---

## 2. M0 状态

```text
✅ P0-2 备份恢复演练（本次）
✅ P0-5 ai_gateway 清零
🟡 P0-3 67%，48h 观察至 2026-11-11 14:13Z
❌ P0-1 3 条 provider + 本地 Key 全 401，需新 Key/控制台
🟡 P0-4 契约已合入；需迁移 lanhu/xhr/playground 浏览器 + 发布窗口
→ batch-279 仍不启动
```

---

## 3. 硬约束（下一次触碰生产前）

1. **部署当前 main 会触发 20261007 的 104 表 DROP**（不可逆，downgrade no-op）；必须有发布窗口 + 用户确认 + 新鲜备份；
2. P0-4 的 Dockerfile 改动必须与"迁移三项浏览器依赖"同一批次，不允许单独删 `playwright install`；
3. P0-3 在 48h 后由 `p0-3-watermark.log` 复核；任何一次 >80% 即视为未达标；
4. P0-1 未拿到有效 Key 前，不得声称 AI 能力恢复。

---

## 4. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | 0.5 人日 / 实际 ≈ 40min |
| 缺陷 | 0（无数据损失；未改业务容器） |
| 返工次数 | 1（容器非 root + PYTHONPATH） |
| 根因分类 | 运维环境差异 |
| 下次避免 | 容器内探测脚本统一 `-e PYTHONPATH=/app -w /app`，并避免写 /tmp（非 root 无法删） |

---

## 5. 关联工件

- [PRD-lite](batch-277b-2-ops-evidence-prd-lite.md)
- [QA](batch-277b-2-ops-evidence-qa-report.md)
- [看板](kanbans/DEV-batch-277b-2-ops-evidence.md)
- [执行记录](batch-277b-2-ops-evidence-report.md)
- 证据目录：[p0-evidence](p0-evidence/README.md)
