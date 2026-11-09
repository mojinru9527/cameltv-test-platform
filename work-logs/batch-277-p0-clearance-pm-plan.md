# Batch 277a — AIQE §0 P0 代码侧清零：PM 计划

> **部门**：🟨 PM
> **日期**：2026-11-09
> **输入**：PRD + 13 号 §0 + baseline C-06/C-07

---

## 1. 任务拆分

| 任务 | 内容 | 依赖 | 预估 | 状态 |
|------|------|------|------|:----:|
| **T277a-1** | `ai_client` 去 gateway：删除 exact cache / Shadow / 本地路由分支，直连项目 provider | — | 0.5d | ✅ |
| **T277a-2** | 删除 `app/services/ai_gateway/`（8 文件）+ 6 个 gateway 端点 + 10 个 gateway 配置项 | T277a-1 | 0.3d | ✅ |
| **T277a-3** | 删除 3 个 ai_* model；`AiAgent` → `ExecutionNode`（`app/models/execution_node.py`，表名保留） | — | 0.2d | ✅ |
| **T277a-4** | 迁移 `20261109_b277_drop_retired_tables`：`DROP TABLE IF EXISTS` + downgrade 重建 | T277a-3 | 0.3d | ✅ |
| **T277a-5** | 嵌入本地化（去 `remote` 分支）+ 配置清理 + 旧脚本/测试删除 | T277a-1 | 0.2d | ✅ |
| **T277a-6** | TA-001.5 `scripts/ci/check-p0-ready.ps1` + `alembic_heads.py` + self-test | T277a-4 | 0.5d | ✅ |
| **T277a-7** | ADR-0027/0028/0029 superseded；`docs/ai/local-ai-agent.md` 重写；13 号 §0 状态回写 | — | 0.2d | ✅ |

**合计 ≈ 2.2 人日**（14 号原估 3-5 天含 P0-1..5 全部，代码侧占比合理）。

---

## 2. 依赖与顺序

```text
T277a-1 (ai_client) ─┬─► T277a-2 (删 gateway 目录/端点/配置)
                     └─► T277a-5 (embedding/脚本/测试)
T277a-3 (models) ───────► T277a-4 (迁移)
T277a-4 ───────────────► T277a-6 (守卫脚本)
T277a-2/4/5 ───────────► T277a-7 (文档)
```

---

## 3. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| `AiAgent` 被误删导致节点注册/派发全挂 | 高 | 只移文件不改表；改后 `execution_job_service` / `ai_agent_service` 引用全量替换并跑 18 条协议测试 |
| 迁移 downgrade 重建表结构不一致 | 中 | downgrade 复制原 migration 的 `create_table`；实测 up→down→up 与表存在性 |
| 删除 gateway 端点导致前端/外部调用 404 | 中 | 前端 `api.d.ts` 为生成类型、无调用方；仓库内 grep 无调用；变化记入 QA |
| 守卫脚本误报（例如 heads 解析） | 中 | heads 用 AST helper；self-test 用临时骨架验证绿/红两条路径 |
| `/uitest` 仍依赖控制面浏览器（P0-4 未做） | 高 | 本批不删 Dockerfile 的 playwright 安装，避免打断现行 `/uitest`；277b 一起改 |

---

## 4. 里程碑

| 节点 | 判据 |
|------|------|
| M-277a-A | ai_client/端点/配置清理完成，app 可导入、路径数 265→259 |
| M-277a-B | 迁移 up→down→up 退出码 0，表存在性符合预期 |
| M-277a-C | 守卫脚本 real=FAIL(4/5)、self-test=PASS |
| M-277a-D | 全量 pytest 0 新增失败 + PR checks 绿 |

---

## 5. 交付边界（对 277b/运维）

- 277b 接：P0-4 `/uitest` 剥离（需 node `ui` kind + UiTestRun 状态映射 + 控制面 Dockerfile 去浏览器 + evidence JSON）；
- 运维接：P0-1 Key 轮换、P0-3 磁盘、P0-2 备份演练，产出 `work-logs/p0-evidence/*.json` 后守卫转绿。
