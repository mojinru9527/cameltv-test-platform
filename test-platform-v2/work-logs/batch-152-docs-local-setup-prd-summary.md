# Batch 152 — 文档保鲜 + 空白机搭建引导（PRD-lite）

> **Product (🟦)** | Date: 2026-08-11 | Status: Approved | Mode: light

mode: light
豁免理由: 纯文档 + 内部工具（launcher -InstallDeps）——不引入新接口/新配置/新依赖/新行为，按 SKILL.md 判定轻量批次。
非目标: 数据集参数化注入（C147-8）、知识图谱治理（C147-9）、需求覆盖率/置信度（C126-2/3）、UI 映射回写（C151-1）、孤儿文件清理/env 统一入口（登记 C152-1）不在本批。

## 1. 问题陈述
1. 使用手册 v2.6（2026-07-15）滞后于生产现状（缺 8+ 模块、launcher 路径、148-151 新能力）。
2. frontend README 技术栈标注 ant-design / React Router 6 过时（实际 shadcn/ui + Router 8）。
3. PostgreSQL 迁移指南引用废弃分支 `feature/p1-batch-a-security`。
4. 无空白机搭建引导 docs/local-setup.md；launcher 无 `-InstallDeps`。

## 2. 成功指标
| 指标 | 基线 | 目标 |
|------|------|------|
| 手册 | v2.6/滞后 | v2.7 含模块总览 + launcher + 新能力 |
| frontend README | ant-design/Router 6 | shadcn/ui/Router 8 |
| PG 指南 | 废弃分支 | 指向最新 main |
| 空白机引导 | 无 | docs/local-setup.md + launcher -InstallDeps |

## 3. 验收
- README/PG 指南无过时技术栈/分支引用（grep 验证）。
- 手册版本号 2.7 + 模块总览含新模块。
- local-setup.md 覆盖 Windows/macOS 步骤；launcher `-InstallDeps` 安装后端 pip + 前端 npm ci。
- 不破坏任何运行路径（launcher 语法校验 + 无代码行为变化）。

## 4. 技能使用
- cameltv-doc-check → 文档保鲜核对
