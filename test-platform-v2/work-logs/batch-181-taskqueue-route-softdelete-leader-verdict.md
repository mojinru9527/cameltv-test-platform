# Batch 181 — Leader 判决：TaskQueue 统一 / 软删统一 / 路由拆分

> **mode: full** | 日期：2026-08-16 | 分支：`feature/batch-181-taskqueue-route-softdelete`

## 1. 判决：✅ APPROVED（待用户一次总确认后推送/PR/合入）

## 2. 抽检与复核

| 工件 | 抽检结果 |
|------|---------|
| PRD | mode:full 判定正确（重构+Schema）；非目标明确（P3 三项、P1-06 状态枚举、硬删转软删均留后续）；C 条件承接表齐全 |
| PM | 19 任务覆盖三 P2 项；切片划分与最终 commit 对应（4 个 commit 可追溯） |
| Design | TaskQueue API 契约落地一致（QueueSpec/atomic_claim/reap/finish/loop）；软删转换表 18 调用点全部落实；拆分映射 9 文件→25 文件与产出一致 |
| Dev | 六队列接入逐项核验（认领/回收/循环）；路由路径集 420 条零漂移（守卫测试）；ORM 禁入守卫 4/4；`== False` 清零断言 |
| QA | 全量 1495 passed / 0 failed；门禁全绿（ruff F821/alembic 单头+升降级/scan-common-bugs 豁免记录）；基线失败集合 6→0 说明完整 |

## 3. 关键风险核验

- **生产执行链安全**：API/AI/DSH/证据包/UI 认领语义与 batch-174 基准逐项对照（reclaim_stale 开关保留 API 原语义；证据包 liveness 保持 heartbeat）；全部队列测试含并发原子性回归。
- **数据安全**：两迁移单头、幂等、可 downgrade；回填仅限存量 deprecated/superseded 值；生产 PG 兼容（server_default 双方言写法）。
- **契约稳定**：OpenAPI 路径集与基线完全一致；前端无 schema 变化，无需 gen:api。

## 4. 遗留与后续条件（写入 C-CONDITIONS.md）

| ID | 内容 | 优先级 |
|----|------|--------|
| C181-1 | 路由层禁 ORM 剩余收敛：非本批 9 域的既有路由文件（defect/report/open_api/perf_ws/playground/token/integration/ui_test/auth/organization/project 等）仍含直连查询，后续批次按 `backend/CLAUDE.md` 约定逐域收敛（守卫测试允许名单可随收敛缩小） | P2 |
| C181-2 | P1-06 执行状态机 4 套取值统一（pending/running/passed/failed/skipped/cancelled）尚未开工（PRD 非目标），TaskQueue 基类已就绪，建议下一架构批次承接 | P1 |
| C181-3 | P3 打磨三项（追溯轴标签/域命名体系/>800 行页面）随迭代自然消化，不设专项 | P3 |

## 5. 知识审计

- 本批产出可入库知识：TaskQueue 统一原语模式、删除语义唯一约定、路由层禁 ORM 约定 → 已写入 ADR-0019 与 backend/CLAUDE.md（仓库级交付物）。
- 与既有 KB 矛盾核对：batch-174 的 API 认领实现（skip_locked）被更可移植的条件 UPDATE 替代——ADR-0019 已记录取舍理由，不构成矛盾（行为等价且更统一）。

## 6. 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 子代理拆分易引入调用签名漂移（confirm_prod 缺失/uuid 导入缺失） | 集成期全量 pytest + F821 捕获；后续委托拆分任务必须附「集成后全量回归」步骤 | QA 报告复盘卡 |
| 守卫测试必须先于重构落地 | 本批 test_route_inventory 先落地，拆分全程零漂移 | SKILL.md 无需改动（已强调测试证据） |
| 删除语义设计需兼顾 UI 展示 | status 保留作展示值、过滤走 is_deleted——写入 backend/CLAUDE.md 强制约定 | 约定文档 |
