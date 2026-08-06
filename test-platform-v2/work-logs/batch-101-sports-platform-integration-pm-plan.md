# Batch 101 — PM Plan（体育平台承接）

> **PM (🟨)** | Date: 2026-08-06 | Status: Review

## 切片拆解

| # | 任务 | 描述 | 验收标准 | 涉及文件 |
|---|------|------|---------|---------|
| 1 | 接入脚本 | `scripts/sports/onboard-sports-platform.py`：登录→Token→契约导入→环境→UI 任务→AV→定时 | 脚本可重复执行，dry-run 支持 | `scripts/sports/onboard-sports-platform.py` |
| 2 | 本地验证 | 本地后端跑通全流程（payload 校验） | 契约导入/任务/计划/schedule 创建成功 | 本地后端 |
| 3 | 生产执行 | 对 Railway 生产执行接入 + 触发 UI 冒烟 | 资产/任务落库；UI run 真实浏览器结果可查 | 生产 API |
| 4 | 证据/文档/条件 | 执行记录 + 文档 + C-CONDITIONS | 证据 JSON；文档更新；audit 0 硬错 | `docs/**`、`C-CONDITIONS.md` |
| 5 | QA + Leader | 门禁 + 工件 | 全绿 | `test-platform-v2/work-logs/batch-101-*` |

## 依赖与顺序

1 → 2 → 3 → 4 → 5。生产执行前必须本地验证通过。

## 范围外

Test5 内网验收（S2）、iOS、运营后台登录链路、旧数据迁移。
