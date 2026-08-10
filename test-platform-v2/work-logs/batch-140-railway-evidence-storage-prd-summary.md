# Batch 140 — Railway 持久卷接入蓝湖证据存储 PRD-lite
> **Product (🟦)** | Date: 2026-08-10 | Status: Approved

mode: light
豁免理由: 交付"Railway 持久卷接入"运维 runbook + 后端启动落点日志 + 生产 env 示例，属部署文档与最小后端加固，无新接口/配置/依赖。

## 1. 问题陈述
Railway 每次部署重建容器文件系统，`/app/storage`（蓝湖证据截图/导出）为临时目录 → 部署后旧截图丢失 → 下载报 `资产文件缺失 404`。需要持久卷挂载 + 明确的落点日志 + 生产配置示例。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 接入路径 | 无文档 | 提供 Railway 卷挂载 runbook（Dashboard/CLI/验证） | 本批验收 |
| 落点可见 | 无 | 后端启动日志打印存储落点 | 本批验收 |
| 生产配置 | 无 | production.env.example 含 LANHU_EVIDENCE_STORAGE_DIR | 本批验收 |
| 回归 | - | 后端导入/F821 无新增失败 | 本批验收 |

## 3. 非目标与 C 条件
- 不迁移对象存储（后续可选）；不改变采集/上传逻辑。
- C140-1 由本批提供接入方案；实际在 Railway 控制台加卷由用户执行（需 Railway 账号）。

## 4. 用户故事与验收标准
- As 运维, I want 知道怎么给 Railway 后端加持久卷, so that 蓝湖截图部署重建后不丢。
  - Given 按 runbook 在 Railway 加卷挂载 /app/storage / Then 部署重建后截图仍可访问。
- As 运维, I want 启动日志显示存储落点, so that 能确认卷挂载生效。

## 5. 技术考量
- 后端 `_storage_base()` 启动时 mkdir + 日志打印；默认 `/app/storage/lanhu-evidence`（容器内）。
- production.env.example 显式 `LANHU_EVIDENCE_STORAGE_DIR=/app/storage/lanhu-evidence`。
- 已丢失旧截图不可找回；加卷后新采集持久。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本批（test） | 运维 | 文档/日志/示例齐全；后端门禁通过 |
| 生产 | 用户 | 按 runbook 加卷后，新采集截图跨部署保留 |

## 7. 技能使用
- `cameltv-agent-team` / `cameltv-deploy`（部署拓扑与卷挂载）。
