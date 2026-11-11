# M3（Phase 3：Explorer + Adapter + Agent + Profile + Detectors）收口报告

> **日期**：2026-11-12 · **范围**：TA-016 → TA-024.2（10 批 + Oracle 守卫）
> **结论**：M3 全部任务完成并合入 main；生产 `20261117` 已上线（106 表）。

## 1. 批次

| 批次 | TA | 内容 | PR |
|------|----|------|----|
| batch-291 | TA-016 | Playwright MCP Explorer PoC（DOM/A11y + 域名白名单） | #520 |
| batch-292 | TA-017 | TesterArmy Adapter（固定版本 + 二次重放 + 产物转换） | #521 |
| batch-293 | TA-018 | Keploy Adapter（依赖捕获 + 回放稳定 + 脱敏 + eBPF 审计） | #522 |
| batch-294 | TA-019 | Agent Service + A0 Requirement Agent（30 样本） | #523 |
| batch-295 | TA-020 | A2 Test Design/Review（P0 断言强制、50 样本） | #524 |
| batch-296 | TA-021 | A3 Workflow Planner（20 标注工作流、禁止自批） | #525 |
| batch-297 | TA-020.3 | Oracle 来源守卫 CI（`check-oracle-layer.ps1`） | #526 |
| batch-298 | TA-022 | Execution Profile / 数据隔离（三档 + checksum + fixture 锁） | #527 |
| batch-299 | TA-023 | Interference Detectors（10 类信号、纯函数） | #528 |
| batch-300 | TA-024 | A4 Failure Triage（12 类、UNKNOWN、禁止自动关缺陷、100 样本） | #529 |
| batch-301 | TA-024.2 | Noise Hint Agent（Skill + 参考实现、证据前缀） | #530 |

## 2. 数据模型

| 迁移 | 表 |
|------|----|
| `20261116_ta019_agent_executions` | `agent_executions` |
| `20261117_ta022_execution_profiles` | `execution_profiles` |

生产迁移链：`20261115 → 20261116 → 20261117`（head），表数 104 → **106**。

## 3. 测试与质量

- 后端全量：**1562 passed / 43 skipped**（M3 新增 89 条）；
- ratchet：ruff 768→400、mypy 193→89，**PASS**；
- 前端未改（M3 全部后端/脚本/Skill）；
- CI：oracle 守卫已接入 `ai-delivery-policy`（self-test + 变更文件扫描）。

## 4. 生产部署

| 项 | 结果 |
|----|------|
| 备份 | `pre-m3b-20261111-235938.dump`（174MB，sha256 `68b0bf02…`） |
| 镜像 | `cameltv-tp-backend:release-m3b-20261111` → `:main`（delta） |
| 迁移 | `20261116 → 20261117_ta022_execution_profiles` |
| 表 | 105 → **106**（`execution_profiles` 已确认） |
| 健康 | `https://swiftbugs.cn` health=200 |
| 回滚 | `prev-m3b` 保留 |
| 磁盘 | 81% |

## 5. 遗留（不阻塞 M4）

| 项 | 说明 |
|----|------|
| 真实浏览器/设备 E2E | Explorer/TesterArmy 目前 fake/脚本契约 |
| 真实 Keploy eBPF | 权限门禁已落，实际录制待专用节点 |
| MCP SDK 封装 | Explorer 仅 `handle_tool` 纯函数 |
| A1/A5+ Agent | 目前 A0/A2/A3/A4 + Noise Hint |
| 归因/信号入库 | `triage_cases` / `interference_observations` 表未建 |
| Profile 审批 UI | API 未开放 |
| 条件边/SSE 长连接/Console 菜单 | 既有遗留 |

## 6. 下一步

M4：TA-025+（按 §19 排期），优先补齐「归因/信号持久化 + 缺陷草稿闭环」。
