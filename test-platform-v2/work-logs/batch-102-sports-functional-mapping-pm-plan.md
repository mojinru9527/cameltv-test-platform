# Batch 102 — PM Plan（体育平台功能模块梳理）

> **PM (🟨)** | Date: 2026-08-06 | Status: Review

## 切片拆解

| # | 任务 | 描述 | 验收标准 | 涉及文件 |
|---|------|------|---------|---------|
| 1 | 批次工件 + 导入脚本 | PRD/PM/Design/看板 + `scripts/sports/import-sports-requirements.py`（需求上传/提取确认/用例生成导入/知识入库/模块关联，dry-run 支持） | 六件工件齐全；脚本可重复执行、dry-run 通过 | `test-platform-v2/work-logs/batch-102-*`、`scripts/sports/import-sports-requirements.py` |
| 2 | 需求文档导入生产 | 用户端原型（98 页）+ 运营后台原型（72 页）md 导入 → extract → confirm | 2 份文档 upload 200、extraction confirmed、文档可查 | 生产 API |
| 3 | 生产页面功能模块勘察 | www.camel1.tv 用户端 + 运营后台 + konfi 关联勘察（真实浏览器文本快照 + 截图） | 模块清单与需求文档逐项对照表；截图留存 | `docs/体育平台-功能模块地图.md`、evidence |
| 4 | 功能用例生成与导入 | AI generate（use_extraction）→ 用例评审/导入 → 域/模块建好 → 脑图导出 | 功能用例落库；`/test-cases/export/xmind` 可导出 | 生产 API、`/test-cases/domains` |
| 5 | 知识中心与模块关联 | 知识源入库 + 图谱实体/关系 + requirement-modules（模块树/全局导航/admin-links/konfi 配置关联） | sources>0、graph 实体/关系可查、admin-links 含用户端↔运营后台↔konfi | 生产 API |
| 6 | 功能地图文档 + 障碍登记 + C 条件 | 模块矩阵文档、平台使用障碍登记（改进任务 backlog）、C-CONDITIONS 更新 | 文档/登记完整；audit-cconditions 0 硬错 | `docs/体育平台-功能模块地图.md`、`docs/改进任务backlog.md`、`C-CONDITIONS.md` |
| 7 | QA + Leader + 一次总确认 | 门禁/证据/判决/复盘卡/流程回写；用户一次总确认 → push → Draft PR → checks → 合入 | QA 报告证据驱动；audit 0 硬错；PR 合入 main | `test-platform-v2/work-logs/batch-102-*` |

## 依赖与顺序

1 → 2 → 3 → 4 → 5 → 6 → 7。生产执行前脚本先 dry-run；AI 生成依赖 extract confirm 完成。

## 范围外

接口用例/接口自动化、UI 自动化、Test5 内网、运营后台生产账号、性能优化（C99-1）、iOS 真机（CP-C2/C84-1）、冒烟放行策略（C101-1）、AV URL（C101-2）、内网 schedule（C101-3）。
