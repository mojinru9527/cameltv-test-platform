# Batch 146 — 蓝湖重试领取与预览页码修复 QA 报告
> **QA (🔍)** | Date: 2026-08-11 | Verdict: PASS（待用户总确认后可推送）

## 范围与证据策略
- 本批直接修改蓝湖证据路由与需求页截图预览，未复用对应模块的旧通过证据。
- 新增增量证据：创建/重试后唤醒 worker 的后端回归；过期初始页码的前端组件回归。

## 可执行门禁
| 门禁 | 命令 | 退出码 | 结果 |
|---|---|:---:|---|
| 后端 F821 | `ruff check app --select F821` | 0 | PASS |
| 后端相关回归 | `pytest tests/test_lanhu_evidence_worker.py tests/test_task_worker.py -q` | 0 | PASS，26 passed |
| 前端组件回归 | `npm test -- --run src/pages/requirement/components/__tests__/PrototypePreview.test.tsx` | 0 | PASS，3 passed |
| 前端类型检查 | `npm run typecheck` | 0 | PASS |
| 前端生产构建 | `npm run build` | 0 | PASS |
| 通用缺陷扫描 | `pwsh scripts/git/scan-common-bugs.ps1` | 1 | 非本批基线：`backend/app/main.py:87` 存量 `except: pass`；本批新增 HARD 为 0 |

## 验收结果
| 验收标准 | 结果 | 证据 |
|---|:---:|---|
| 创建任务立即尝试领取 | ✅ PASS | `test_create_job_kicks_evidence_worker_after_persisting` |
| 重试任务立即尝试领取 | ✅ PASS | `test_retry_kicks_evidence_worker_after_persisting` |
| 原任务与重试尝试隔离 | ✅ PASS | `test_retry_creates_immutable_attempt_and_preserves_original` |
| 过期页码不再显示 10/7 | ✅ PASS | `clamps an obsolete initial page index to the available page range`，断言第 7/7 页 |

## 缺陷列表
- 本批新增缺陷：无。
- 已知外部/存量风险：蓝湖 Cookie 或上游发现接口不可用仍可令采集失败；本批保证失败后的重试任务会被立即尝试领取，但不伪造上游采集成功。

## CI 分类
- 预计分类：backend + frontend 混合变更；PR required checks 应运行双域检查。

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 2h / 实际约 1.5h | 0/0/0/0 | 0 | 技术债 | 对异步持久化队列在提交/重试路径加入“即时唤醒 + 定时兜底”回归断言。 |
