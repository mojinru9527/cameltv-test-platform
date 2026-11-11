# M4（Phase 4：归因实验 + 缺陷闭环 + 噪音规则 + 平台矩阵）收口报告

> **日期**：2026-11-12 · **范围**：TA-025 → TA-028（5 批）
> **结论**：M4 全部任务完成并合入 main；生产 `20261121` 已上线（109 表）。

## 1. 批次

| 批次 | TA | 内容 | PR |
|------|----|------|----|
| batch-303 | TA-025 | Counterfactual Replay（E1-E6、单变量、幂等、verification_run_id） | #532 |
| batch-304 | TA-026 | Defect Draft + Link（结构化步骤/证据/AC、详情页） | #533 |
| batch-305 | TA-027 | 一键回归（defect_regressions、四分类对比、Dialog/Compare） | #534 |
| batch-306 | TA-027.3 | Noise Rules（90 天强制复核、永久 quarantine 拒绝） | #535 |
| batch-307 | TA-028 | Platform Matrix（AC × 多端、独立证据、跨端语义） | #536 |

## 2. 数据模型

| 迁移 | 表/字段 |
|------|---------|
| `20261118_ta025_triage_experiments` | `triage_experiments` |
| `20261119_ta026_defect_aiqe_link` | `defect` + aiqe_run_id / node_run_id / reproduction_steps / evidence_refs / ac_refs / is_draft |
| `20261120_ta027_defect_regressions` | `defect_regressions` |
| `20261121_ta0273_noise_rules` | `noise_rules` |

生产迁移链：`20261117 → 20261121`（head），表数 106 → **109**。

## 3. 测试与质量

- 后端全量：**1592 passed / 43 skipped**；
- 前端全量：**560 passed**；typecheck/build 通过；
- ratchet：ruff 768→400、mypy 193→89，**PASS**；
- 路由基线：322 → 323。

## 4. 生产部署

| 项 | 结果 |
|----|------|
| 备份 | `pre-m4-20261112-014811.dump`（174MB，sha256 `af5c4d1d…`） |
| 镜像 | `cameltv-tp-backend:release-m4-20261112` → `:main`（delta） |
| 迁移 | `20261117 → 20261121_ta0273_noise_rules` |
| 表 | 106 → **109**（triage_experiments / defect_regressions / noise_rules） |
| 健康 | health=200 |
| 回滚 | `prev-m4` 保留 |
| 磁盘 | 81% |

## 5. 遗留（不阻塞 M5）

| 项 | 说明 |
|----|------|
| 真实回归 Run 触发 | `verification_run_id` 由调度器后续接入 |
| Noise Rules CRUD 页面 | 已有表格组件，缺独立页面/路由 |
| Platform Matrix 后端 binding 表 | 前端矩阵组件已就绪 |
| 真实 E2E/eBPF | Explorer/TesterArmy/Keploy 仍为契约/模拟 |
| 条件边/SSE/Console 菜单 | 既有遗留 |

## 6. 下一步

M5：按 §19 后续任务（TA-029+）。
