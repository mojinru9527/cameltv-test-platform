# Batch 162 — Leader Verdict

> **Leader (🎯)** | Date: 2026-08-12 | Decision: APPROVED

## 评审摘要
| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | 4/5 | 六件齐全；迁移幂等；回归测试 5 个新增 |
| 风险 | 低 | C161-1 生产 E2E 依赖用户配置蓝湖凭据（外部项，已文档化） |
| 覆盖 | 高 | 三条件代码闭环 + 门禁全绿 |

## 关键决策（已批准）
1. C161-2 属 Schema 变更 → 本批按完整批次执行（PRD/PM/Design/Dev/QA/Leader 六件）。
2. C161-1 平台侧修复（持久卷 + 文档）；生产自动登录最终依赖 Railway LANHU_USERNAME/PASSWORD（用户配置项）。
3. C161-3 以分类规则为主 + 回填脚本，展示侧即时生效。

## 抽检通过
- ✅ `schedule_service._ensure_schedule_env` + scheduler 透传 environment_id
- ✅ 迁移幂等（_has_table/_has_column + revision ≤32）
- ✅ Dockerfile/compose DATA_DIR 统一持久卷 + 契约测试
- ✅ classify_case_surface 新增 9 域 + 回填脚本

## 判决
**APPROVED** — 合入门禁全绿；合入 + 部署后执行生产复验（C161-2 调度触发 / C161-3 surface / C161-1 凭据配置后采集）。

## 流程回写
| 发现 | 处理 | 落点 |
|------|------|------|
| 新迁移 revision 超 32 字符导致 version_num 溢出 | 缩短为 20260812_b162_sched_env + 回归测试 | alembic/versions/ |
| 修改 Dockerfile 后 compose 契约测试不同步 | 同步 compose DATA_DIR + 更新契约断言 | deploy/docker-compose.yml、tests/test_deploy_compose_contract.py |
| 调度触发 API 计划缺环境是配置缺口而非执行引擎问题 | 增加 environment_id 绑定 + 创建期校验 | schedule_service/scheduler/frontend |

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 1d vs 0.5d | 0/0/1/1 | 2 | 迁移/部署契约 | 迁移与 Dockerfile 改动先跑全量 + 契约测试 |
