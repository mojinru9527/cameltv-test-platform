# Batch 101 — QA 报告（体育平台生产接入）

> **QA (🔍)** | Date: 2026-08-06 | Verdict: PASS（生产接入完成）；UI 冒烟 3/5 为真实发现，如实登记

## 测试总览

| 项 | 通过 | 失败 | 阻塞 |
|:---|:----:|:----:|:----:|
| 接入脚本本地全流程验证 | ✅ | 0 | 0 |
| 生产契约导入（7 服务 / 899 端点） | ✅ | 0 | 0 |
| 用例生成 + 测试计划（325 条） | ✅ | 0 | 0 |
| 生产环境 / UI 冒烟任务 / Token | ✅ | 0 | 0 |
| 生产 UI 冒烟真实浏览器执行 | 🟡 3/5 | 2 | 0 |
| 门禁（audit/boundary/保鲜） | ✅ | 0 | 0 |

## 可执行门禁（命令 + 退出码）

| # | 门禁 | 结果 |
|---|------|------|
| G1 | 接入脚本 py_compile | exit 0 |
| G2 | 本地后端全流程（dry-run + 真实） | 899 端点 + 325 用例 + 计划/环境/任务/schedule 全创建 |
| G3 | 生产执行 `onboard-sports-platform.py` | exit 0（Railway） |
| G4 | 条件审计 `audit-cconditions.ps1 -RequireLatestBatch` | 0 硬错 |
| G5 | 边界 `validate_repo_boundaries.py --check` | PASS |
| G6 | 保鲜 `check_doc_freshness.py` | exit 0 |

## 生产接入结果（Railway）

| 项 | 值 |
|---|-----|
| 服务导入 | account / api-gateway / camel-mimo / camel-service / live-platform / payment / studio（899 端点） |
| 计划 | 体育平台-每日回归（camel-service 325 用例） |
| 环境 | 体育平台-生产（prod，https://www.camel1.tv）+ 5 变量（允许清单/期望文本/owner/登录授权） |
| UI 任务 | 体育平台-生产只读冒烟（specs/production-smoke.spec.ts，chromium） |
| 定时任务 | 体育平台-每日API回归（已停用——Test5 内网不可达，内网回归由 CI 承担） |
| CI Token | sports-ci（已生成，请保存） |

## UI 冒烟（run 4，真实浏览器）

| 结果 | 说明 |
|------|------|
| 3/5 通过 | TC-PROD-003 导航面 / TC-PROD-004 核心 API 资产 / TC-PROD-005 15s 基线 |
| TC-PROD-001/003 拦截 | 站点发射 **POST 信标** + 加载非白名单**广告域**（ukankingwithea.com / dstimaariracon.org / allowtohimselfew.org）——严格只读守卫正确拦截，属真实发现（C101-1） |
| TC-PROD-002 登录 | 需显式授权 + 生产业务账号（不提供），按契约失败（非平台缺陷） |

## 缺陷与遗留

| # | 级别 | 内容 | 处理 |
|---|:----:|------|------|
| B101-Q1 | P1 | 生产首页含 POST 追踪与第三方广告域，严格只读冒烟无法全绿 | C101-1 放行策略评估（不静默放行） |
| B101-Q2 | P2 | 音视频任务真实回放 URL 未提供 | C101-2 待业务提供 |
| B101-Q3 | P2 | Test5 内网 API 回归从公网后端不可达 | schedule 停用 + C101-3；内网由 CI 承担 |
| B101-Q4 | P3 | 管理员凭据遗忘恢复：admin 已重置 + 新建 sportsadmin（用户授权） | 凭据已交付；建议用户改密并同步 production.env |

## 发布建议

状态：**READY**（生产接入完成；冒烟发现如实登记，不伪造全绿）。

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1d / 实际 1d | 0/1/2/1 | 3（spec 路径/允许清单迭代/登录授权） | 外部依赖+契约 | 冒烟先本地跑通再上生产；允许清单按真实页面资源迭代 |

**技能使用**：`cameltv-agent-team`
