# Batch 68 — PRD Summary（AI 验收全链路 + 正式域名发布演练）

> **Product (🟦)** | Date: 2026-08-03 | Status: Approved（用户已确认执行器 Codex 并授权启动）

## 1. 问题陈述

1. **AI 验收全链路仍未闭环（G56-011，P0）**：C55-3 Knowledge/Wiki/Trace 深层功能未以「当前真实输入」完成
   J06（蓝湖证据包 + OCR + 需求导入）、J07（知识/RAG/Wiki/Agent 真实 AI 无 fallback）、J13（质量追溯同源钻取）
   的 P/N 原子结果。前置条件已解锁（2.1 AI Key 实测 200、2.2/2.3 登记 ✅、6.1 Railway 部署 ✅），本批具备执行条件。
2. **G56-012（P0）**：C55-4 的本地引用、审计、失败转缺陷和调度语义仅有缩小版证据，尚缺完整真实
   UI/API/DB/报告/通知正负面旅程。
3. **G56-014（P0）**：J03/J08/J09/J15/J16 与真实 UI 主链、J19 全资源横向矩阵仍未闭环。
4. **C67-3（P2）**：蓝湖 Cookie 有效期未运行期实测（lanhu-mcp 登录态），失效需重新获取。
5. **正式域名发布演练未执行**：Vercel `https://cameltv-test-platform1.vercel.app` 与 Railway
   `https://test-platform.up.railway.app` 已上线且 `/api` 反代 200（#101/#102 后），正式域名发布演练具备条件。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| G56-011 | OPEN | J06/J07/J13 的 P/N 原子结果全部 PASS；规则 fallback、固定“未同步”展示不计通过 | 本批 QA |
| G56-012 | OPEN | C55-4 真实 UI/API/DB/报告/通知正负面旅程证据完整 | 本批 QA |
| G56-014 | OPEN | J03/J08/J09/J15/J16、真实 UI 主链、J19 横向矩阵闭环 | 本批 QA（J16 受媒体样本授权限制时 DEFERRED） |
| C67-3 | Open（P2） | lanhu-mcp 启动实测 Cookie 有效或重新获取后有效，登记证据 | 本批 Slice 1 |
| 正式域名发布演练 | 未执行 | 生产域名全链路（登录/首页/API/健康）实测证据 + 发布决策登记 | 本批 |

## 3. 非目标（本次不做）

- **不处理 C58-01/03/04**（Cloudflare 站点、Supabase 运行证据、`production.env` 回填）——外部未解锁项，维持 OPEN。
- **不迁移 V1 工具（C64-1）**、**不做垃圾文件审计删除（C64-2）**——与本批无关。
- **不做 API-only UI（C63-1）**——继续顺延。
- **不做真机性能采集（CP-C1/C2）**——需物理设备，保持 BLOCKED。
- **不做 Test5 六服务实时契约（G56-003/004 之外的外部授权项）**——Test5 窗口另批执行（1.1 已登记 2026-08-03 11:00–18:00）。
- **不伪造证据**：缺授权/缺数据时对应 J 项登记 DEFERRED，禁止用历史材料冒充当前执行（C63-2）。

## 4. 用户故事 + 验收标准

- As a 平台负责人，I want 用真实蓝湖设计源 + 真实 AI/OCR 跑通知识链，so that AI 验收不因假解锁返工。
  - 验收：Given R0-LANHU-USER/ADMIN 可访问 / When 采集证据包 → OCR → 导入需求 / Then J06 P/N 全过且附件失败可观察处理。
- As a QA，I want 真实 LLM/OCR 服务调用证据（无 fallback），so that G56-006 的“假结论”风险被排除。
  - 验收：Given R0-AI-LIVE 配置有效 / When J07 执行摄取/检索/Wiki/Agent / Then 输出引用真实来源、服务失败时可重试且无假结论。
- As a 验收人员，I want 生产域名全链路可用证据，so that 正式域名发布决策可登记。
  - 验收：Given Vercel+Railway 在线 / When 演练登录/首页/API/健康 / Then 全部 200 且 ALLOWED_ORIGINS 与新域名一致。

## 5. 技术考量

- 数据资产：R1-USER-REQ / R1-ADMIN-REQ / R1-TRACE-V14（108 条追溯种子）/ R1-USER-CASES / R1-ADMIN-CASES 已在仓库登记 SHA。
- 外部依赖：lanhu-mcp（Cookie 在 gitignored .env）、PaddleOCR 本地（需装 paddleocr+paddlepaddle）、DeepSeek Key（已 200）。
- 运行拓扑：本地 backend（8035）+ frontend（5205）+ lanhu-mcp server（8000）+ OCR venv；生产演练走 Vercel/Railway。
- 已知风险：蓝湖 Cookie 过期、PaddleOCR 首次模型下载耗时/网络、J16 媒体样本授权、J15 外部页面授权 → 对应 DEFERRED 不伪证。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| Slice 1 环境+C67-3 | QA/Dev | lanhu-mcp 启动、Cookie 实测有效、依赖就绪证据 |
| Slice 2 J06 | QA | 证据包采集→OCR→导入→需求追溯闭环 P/N PASS |
| Slice 3 J07 | QA | 知识/RAG/Wiki/Agent 真实 AI 闭环、无 fallback 证据 |
| Slice 4 J13 + G56-012/014 | QA | 追溯同源钻取、UI 主链、横向矩阵、报告/通知正负面 |
| Slice 5 正式域名发布演练 | 用户/QA | 生产域名全链路 200 + 发布决策登记 |
| 收口 | Leader | QA PASS + Leader APPROVED + PR 合入 |

## 7. 条件对账（C-CONDITIONS.md）

- **纳入**：G56-011、G56-012、G56-014（P0）；C67-3（P2）；C65-3（逐项解锁登记）；C63-2（禁止假证据）；C63-3（引用 C63 条件）。
- **已关闭引用**：C67-1（AI Key 200）、C67-2（Railway URL）、C58-02（Vercel 公开 200）、C58-06（反代回填）——#97/#101 完成。
- **豁免**：C58-01/03/04、C63-1、C64-1、C64-2、C66-4、CP-C1/C2、G56-003/004 外部授权项（理由见 §3）。
- **不关闭**：J16/G56 媒体与外部页面授权项，无样本时保持 DEFERRED/BLOCKED。
