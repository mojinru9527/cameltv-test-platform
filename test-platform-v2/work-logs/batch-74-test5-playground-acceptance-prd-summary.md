# Batch 74 — PRD Summary（Test5 契约登记 + Playground 实证 + J15/J16 验收）

> **Product (🟦)** | Date: 2026-08-04 | Status: Approved（用户确认执行器 Codex 并授权启动；Test5 契约地址已提供）

## 1. 问题陈述

batch-73 收口交付决策后，剩余三类用户侧/内部待办具备推进条件：

1. **Test5 六服务契约（C65-3 / 外部前置条件 1.4）**：用户已提供测试环境接口
   `http://camel-api-gateway05.svc.elelive.cn/camel-service/doc.html#/home`
   （`camel-service` 为服务名模式）。网关路由表实测暴露 10 个服务，需拉取 OpenAPI
   契约并登记（服务名/地址/版本/路径数/SHA-256），为 V1~V5 验收矩阵提供真实输入。
2. **Playground（C22-C2 / C22-C3 / C72-2）**：`POST /playground/compile` 目前对
   中文 Gherkin 步骤只输出 `// TODO` 骨架，`execute` 链无实证；需完成
   Gherkin→Playwright 步骤映射改造并跑通 C22-C2（单条链路实证）与 C22-C3
   （6/6 批量 + 报告），之后把 Playground 从 API-only 转为正式 UI。
3. **J15 / J16（C68-1 / C69-1）**：用户已授权外部只读页面
   `https://www.camellofutbol.com` 与「match replays」媒体样本；需执行对应
   正负面验收并登记证据（外部页 UI 自动化 + 真实媒体 av-checks）。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| Test5 契约 | 仅 1 个 URL 文字 | ≥10 服务契约清单（SHA-256/版本/路径数）登记；契约文件落库可复现拉取 | 本批 |
| Playground 编译 | 中文步骤出 TODO 骨架 | 中文 Gherkin 步骤映射为可执行 Playwright 动作，无 TODO，tsc 编译通过 | 本批 |
| C22-C2 | 无实证 | 真实页面执行 + 截图 + 平台执行记录 | 本批 |
| C22-C3 | 无实证 | 6/6 批量执行 + 报告自动生成可导出 | 本批 |
| J15 | 授权待执行 | 外部页真实浏览器打开 + 断言 + 截图登记 | 本批 |
| J16 | 授权待执行 | match replays 真实媒体 av-checks 结果登记 | 本批 |

## 3. 非目标

- **真机（CP-C1/C2）**：用户今晚回来再排，本批不执行。
- **ELK（3.4）/ 旧库快照（5.1）/ 制品库 / Secret 管理 / 备份恢复门禁**：外部未提供，保持 DEFERRED。
- **不改变 production 发布状态**（仍为 DEFERRED，ADR-0015 门禁未全绿）。
- **不新增第三方依赖**：Playwright / ffprobe 均已具备。
- 不处理与以上三条无关的历史孤儿条件（保留 C-CONDITIONS Open 状态）。

## 4. 条件对账

- **纳入**：C22-C2、C22-C3、C72-2、C70-1（转正式 UI 决策）、C68-1、C69-1、
  C65-3（1.4 契约部分）、C66-4（网关/节点 IP 补充登记）、C63-2（登记口径遵守）。
- **豁免/延后**：CP-C1/C2（真机今晚）、ELK（依赖 VPN/WSL 解锁，Test5 网段已通可后续补）、
  旧库 5.1（无快照）、生产发布门禁、Cloudflare（batch-73 已豁免登记）。

## 5. 证据与 KB 检索说明

- 本批开发/验收前检索知识库（`platform_knowledge` / `defect_case`）不可用（本地 RAG 服务未运行），
  以 `C-CONDITIONS.md`、`docs/production-delivery/*`、`work-logs/` 历史工件、
  `cameltv-bug-guard` 避坑清单作为替代核查基线（在 QA 报告中记录）。
