# Batch 150 — Leader Verdict（请求缓存/防抖/退避 + mindmap 聚合）

> **Leader (🎯)** | Date: 2026-08-11 | Decision: APPROVED

## 评审摘要
| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | 4.5/5 | 缓存/去重契约清晰，TTL + 显式失效 |
| 风险 | 低 | 仅前端；缓存 60s + CRUD 清理，signal 路径绕过缓存 |
| 覆盖 | 4.5/5 | 455 vitest + Network 冒烟量化 |

## 关键决策（已批准）
1. 缓存仅用于低频静态 GET（menus/environments/domains），TTL 60s，CRUD/401/登出显式清理；传 signal 时走原路径保 abort 语义。
2. mindmap 放弃客户端全量构建，改用已有 `/test-cases/taxonomy` 服务端聚合（叶子为模块计数）。
3. 轮询退避上限 30s，收到数据立即复位 500ms。

## 抽检通过
- ✅ client.ts cachedGet/clearApiCache（单测 4/4）
- ✅ mindmap index.tsx 数据流（taxonomy → surface/domain 过滤 → markdown 计数树）
- ✅ integration 探针移除（2 处）
- ✅ 冒烟证据 evidence/batch-150/（menus/env/domains ×1 + mindmap-taxonomy.png）

## 判决
APPROVED → 按用户一次性授权推送、创建 Draft PR，required checks 全绿后合入 main。
合入后关闭 C147-5（C146-3 承接一并关闭）。

## 下一批次 Leader 条件
- 无新增；Batch 151 承接 C147-6（功能用例入计划 + 四者关联 + 失败自动链路）。

## 流程回写
| 发现 | 处理 | 落点 |
|------|------|------|
| 修改 client 导出后旧 vi.mock 缺新导出导致测试挂 | 已修复 testcase.test.ts；后续改 client 导出同步检查 mocks | testcase.test.ts + QA 复盘卡 |

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 4h vs 实际 3h | 0/0/0/0 | 1 | 测试 mock 未同步 | 改 client 导出后同步 mocks |

**技能使用**: cameltv-agent-team 流水线；audit-ai-pr（推送后执行）
