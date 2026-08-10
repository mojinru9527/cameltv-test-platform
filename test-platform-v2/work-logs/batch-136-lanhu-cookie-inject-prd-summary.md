# Batch 136 — 蓝湖保存的 Cookie 真正注入采集请求 PRD-lite
> **Product (🟦)** | Date: 2026-08-10 | Status: Approved

mode: light
豁免理由: 修复既有 Cookie 保存不生效的 bug + 前端提交前校验，无新接口/新配置/新依赖。

## 1. 问题陈述
用户在生产保存"粘贴 Cookie"后，采集任务仍报"蓝湖会话已失效"。根因（实测确认）：
`LanhuExtractor.__init__` 无 `cookie` 参数，请求头读取模块级 `COOKIE`（env LANHU_COOKIE / 占位符）；
后端 `_create_lanhu_extractor` 仅在 extractor 有 cookie 参数时传入，导致**保存的 Cookie 从未注入**，
worker 始终用占位 Cookie → 任务持续"会话失效"。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| Cookie 注入 | 保存后不生效（实测 False） | `_create_lanhu_extractor(runtime, cookie)` 后提取器请求头 Cookie == 传入值 | 本批验收 |
| 前端链接校验 | 无 | 提交前检查 pid/docId，缺失内联提示，不创建坏任务 | 本批验收 |
| 回归 | - | 后端 1313、前端 444 无新增失败 | 本批验收 |

## 3. 非目标与 C 条件
- 不新增后端接口；不保证 Cookie 本身有效（有效由用户粘贴/登录保证）。
- C 条件维持（无新增）。

## 4. 用户故事与验收标准
- As 测试平台用户, I want 保存的蓝湖 Cookie 真正用于采集, so that 会话过期后重新登录/粘贴 Cookie 能恢复采集。
  - Given 用户粘贴并保存 Cookie / When 发起采集 / Then 请求携带该 Cookie；不再因占位 Cookie 报"会话失效"。
- As 测试平台用户, I want 提交前知道链接是否完整, so that 不再遇到"缺 pid"的深层报错。
  - Given 链接缺 pid/docId / When 点击开始采集 / Then 内联提示，不发起创建。

## 5. 技术考量
- 后端 `_load_lanhu_runtime` 暴露 module；`_create_lanhu_extractor` 在 cookie_override 非空时注入 module.COOKIE/DDS_COOKIE 再实例化（兼容有 cookie 参数的新 extractor）。
- 前端 `LanhuEvidenceDialog` 提交前校验 `pid=`/`docId=`。
