---
title: "测试资产底图标准（Test Asset Map Standard）"
owner: "qa-team"
last_reviewed: "2026-11-06"
status: "active"
expires: "2027-05-06"
tags: ["standard", "case-generation", "interaction", "chain", "coverage"]
related: ["../.claude/skills/interaction-case-augmenter/SKILL.md", "interaction-case-augmentation.md", "./project-adapters/"]
---

# 测试资产底图标准

> 解决三个问题：① 换项目能不能复用；② 什么时间做什么事；③ 覆盖到什么程度算够。
> 一句话：**准则与引擎跨项目恒定，项目差异只写适配器，覆盖率按断言与链路计量。**

## 1. 三层复用模型

| 层 | 内容 | 是否随项目变化 | 位置 |
|---|---|---|---|
| **L1 通用资产** | 24 条交互准则 + 断言库、矩阵 Schema、链路分层模型（L1 域内/L2 跨域/L3 补偿）、覆盖率口径、门禁规则、引擎 | **不变**（改一次全项目受益） | `.claude/skills/interaction-case-augmenter/references/interaction-rules.json`、`scripts/test-asset-map/` |
| **L2 项目适配器** | 页面源、接口源、业务域映射、业务闭环、平台清单 | 每项目一份 YAML（约 50–150 行） | `docs/standards/project-adapters/<project>.adapter.yaml` |
| **L3 项目实例** | 84 页清单、2016 格矩阵、34 条域内链、缺陷模式库 | 由引擎自动生成 + 人工校准 | `docs/standards/project-adapters/out/<project>/` |

> 判断一个资产属于哪层的方法：**换项目后需要人工改写的，就是 L2/L3；不需要改的就是 L1**。

### 1.1 复用契约（必须保持稳定的接口）

引擎只依赖以下四件事，任何项目只要提供它们即可复用：

```yaml
pages:        # 页面清单：platform / page_id / group / name / path / page_kind
interfaces:   # 接口清单：method / path / name
domain_map:   # 业务域 = 一组路径前缀（人工校准点）
closures:     # 业务闭环 = 业务域的有序组合（人工校准点）
```

输出格式恒定：`page-inventory.json`、`rule-page-matrix.csv`、`interface-chain-graph.json`、`summary.json`。
**用例模板、缺陷模式库 schema、准则库格式不得随项目改动**；项目差异一律进适配器。

### 1.2 跨项目验证（实测）

| 项目 | 页面源 | 接口源 | 结果 |
|---|---|---|---|
| 未来娃屿 | `sys_menu` + `app.json` 导出（84 页） | Apifox 端点清单（535） | 2016 格 / 适用 1541 / 覆盖 17.3%；34 域 / 未归类 7 |
| CamelTv 体育 | OpenAPI `tags`（4 域） | `cameltv-openapi.yaml`（5 端点） | 96 格 / 适用 76 / 覆盖 0%（无基线）；2 域 / 未归类 1 |

同一份引擎、同一份准则库，**改动只有适配器**。CamelTv 那组"0% 覆盖"不是失败，而是首轮接入的正确输出：直接产出缺口清单。

## 2. 标准作业流程（什么时间做什么事）

| 阶段 | 触发时点 | 必须做的事 | 产出物 | 准出（DoD） | 耗时参考 |
|---|---|---|---|---|---|
| **P0 项目接入** | 新项目 / 换项目 / 新增大端（如新增平板端） | ① 导出页面源与接口源 ② 写适配器 ③ 跑引擎 ④ **人工校准域映射与业务闭环** ⑤ 导入历史缺陷建 Pattern 库 ⑥ 标注环境能力矩阵 | 三份底图 + Pattern 库 + 能力矩阵 | 页面清单覆盖 = 100%；接口分配率 ≥ 95%（未归类 ≤5% 且逐条说明）；Pattern 库 schema 校验通过 | 0.5–1 人天 |
| **P1 需求进入** | 需求评审通过当天 | ① 底图 diff：新增/变更页面与接口 ② 生成「变更影响清单」：受影响页面 × 准则、受影响接口 × 链路 | 影响清单 + 增量矩阵 | 每条新需求 ≥1 个准则覆盖点 + ≥1 个链路节点 | 0.5 人天/迭代 |
| **P2 用例设计** | 需求进入后 1–2 天 | ① 按矩阵 NONE 格生成**参数化用例族** ② 设计链路用例（L1/L2/L3）③ 每条用例绑断言 ID ④ 标执行载体 | 用例集 + 断言台账 + 链路契约（夹具/门禁/清理） | P0 页面断言覆盖 100%、P1 ≥80%、P2 ≥50%；每条链路有夹具链与清理契约 | 2–3 人天/迭代 |
| **P3 执行** | 提测后 | ① P0 链路 → P0 断言 → P1 → 抽样 ② 失败取证 ③ 阻断登记 | 执行报告 + 证据 | 阻断率 ≤10%；每个失败有请求/响应/截图；未执行为 0 条无理由 | 按规模 |
| **P4 缺陷回流** | 缺陷确认当天（不是周末） | ① 定位 `(准则, 页面, 断言)` 三元组 ② **该准则在全部适用页面重算状态** ③ 补断言 → 更新矩阵 ④ 回归锚定 | 更新后的 Pattern 库 + 矩阵 + 复检清单 | 每条缺陷可追溯到三元组；受影响页面状态已重算；同类页面已复检 | 0.2 人天/缺陷 |
| **P5 版本验收** | 发布前 2 天 | ① 覆盖率报告 ② 链路通过率 ③ 历史缺陷复发率 ④ 结论 READY/CONDITIONAL/NEEDS WORK | 验收报告 | 无 P0/P1 未闭环；P0 链路通过率 100%；断言覆盖率达阶段目标；复发率 ≤5% | 0.5 人天 |

### 2.1 关键约束（违反即返工）

1. **P0 未完成不得进入 P2**：没有底图就设计用例，等于凭记忆写。
2. **P4 不得只改那一条用例**：必须按准则在全部适用页面复检（本次 REG-25 只改一条就是反例）。
3. **不得用「用例数」作为验收指标**：只看断言覆盖率、链路通过率、复发率。
4. **不得跳过人工校准**：域映射与业务闭环是唯一必须人工确认的两处（机器只能给候选）。

## 3. 覆盖率口径（统一算法）

| 指标 | 公式 | 目标 |
|---|---|---|
| **断言覆盖率** | 已覆盖格 / 适用格（`rule × page`，覆盖=预期结果中存在该准则断言） | P0 页面 100%，P1 80%，P2 50% |
| **接口分配率** | 已归入链路域的接口 / 全部接口 | ≥95%（剩余逐条说明） |
| **链路可执行率** | 具备夹具链 + 入口门禁 + 清理契约的链路 / 全部链路 | ≥80% |
| **缺陷复发率** | 复发的历史缺陷 / 历史缺陷总数 | ≤5% |
| **阻断率** | 阻塞用例 / 计划用例 | ≤10% |

> 反例（本次实测）：未来娃屿断言覆盖率 17.3%、零覆盖页面 47/84、接口链路分配仅为"域内链"级别而可执行链路 0 条。这些数字比"1230 条用例、需求覆盖 100%"更能说明真实水位。

## 4. 适配器编写指南（换项目只做这四件事）

```yaml
project: <id>
platforms: [ {key, label}, ... ]

pages:
  source: file | openapi_tags | static     # RuoYi→file(sys_menu 导出)；Next/Router→file；纯 API 项目→openapi_tags
  path: sources/<project>.pages.json

interfaces:
  source: endpoints_json | openapi
  path: sources/<project>.endpoints.json
  domain_map:                              # ★ 人工校准点 1：业务域 = 路径前缀组
    - { name: 资产-组件, prefixes: ["/system/component"] }
  default_domain: 其他

cases: { path: sources/<project>.cases.json }   # 首轮可空

business_closures:                         # ★ 人工校准点 2：跨域闭环
  - { id: CLOSURE-ORDER, name: 下单闭环, chain: [资产-组件, 商品-C端, 订单-C端] }

output_dir: out/<project>
```

### 4.1 不同技术栈的页面源取法

| 技术栈 | 页面源 | 取法 |
|---|---|---|
| RuoYi / 后台管理系统 | 菜单表 | `select menu_name,path,component from sys_menu where menu_type='C'` |
| 微信小程序 | `app.json` | `pages` + `subPackages[].pages` |
| Next.js / React Router | 路由文件 | 静态扫描 `app/**/page.tsx` 或 `routes.ts` |
| 纯 API / 中台 | OpenAPI tags | 先按 tag 粗分，后续补网关路由 |
| 硬件 / 平板 App | 手工 + 接口 | 适配器 `pages.source: static` 列出页面 |

## 5. 与现有资产的关系

- 本标准的 L1 准则库是 `interaction-case-augmenter` 的输入，不替代它；
- 底图产出的 NONE 格 = 用例生成的任务清单，生成仍走 `test-case-design` + 增强层；
- 链路图产出的 L1/L2 链 = 接口用例的编排骨架，仍按 `api-checklist.md` 的断言要求落地；
- 历史缺陷仍由 `bug-pattern-curator` 维护，但**每条缺陷必须落到 `(准则, 页面, 断言)` 三元组**。

## 6. 新项目 30 分钟上手清单

1. 准备页面源、接口源两个文件；
2. 复制 `cameltv-sports.adapter.yaml` 改四处（pages/interfaces/domain_map/closures）；
3. 跑 `python scripts/test-asset-map/build_asset_map.py <adapter>`；
4. 看 `summary.json`：未归类接口是否 ≤5%、零覆盖页面清单是否符合预期；
5. 人工校准域映射与闭环（唯一需要脑力的部分）；
6. 把 `summary.json` 的缺口清单排进 P2 用例设计。
