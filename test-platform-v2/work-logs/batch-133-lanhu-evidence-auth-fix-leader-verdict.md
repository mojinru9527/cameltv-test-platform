# Batch 133 — 蓝湖证据采集会话失效/失败状态 Leader Verdict
> **Leader (🎯)** | Date: 2026-08-10 | Decision: APPROVED

## 评审摘要
| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | 通过 | 418/401/403 统一分类为会话失效；证据流明确失败；ai_service 不再吞错兜底；Cookie 安全存储 |
| 风险 | 中低 | 后端新增 2 个接口 + 前端对话框；不触碰 lanhu-mcp 子模块；无生产数据改动 |
| 覆盖 | 通过 | 后端 8 条定向 + 1297 全量；前端 440 全量；浏览器证据 + vision |

## 关键决策（已批准）
1. 418 视为会话失效：httpx 401/403/418 → `_is_lanhu_session_expired`，证据流返回 manual_action_required 明确错误。
2. 失败不伪装完成：ai_service 会话错误透传；前端失败任务 stage 显示"已结束（失败）"，不再用"已完成"掩盖。
3. 重新登录/更新 Cookie：新增 cookie/login 接口；仅存 Cookie 不存密码；自动登录缺失时明确回退粘贴 Cookie（C133-1 满足）。

## 抽检通过
- ✅ `lanhu_provider._is_lanhu_session_expired` + 证据流会话失败单测
- ✅ `ai_service.extract_features` 会话错误不透传兜底单测
- ✅ 浏览器：失败徽标/错误横幅/登录入口/对话框保存 Cookie
- ✅ 前端 440/440、后端 1297（3 失败为子模块环境基线）

## 判决
**APPROVED**。一次总确认（2026-08-10）覆盖推送 + Draft PR + required checks 通过后合入 main；QA 硬门禁全绿。

## 下一批次 Leader 条件
- C134-1：lanhu-mcp 子模块 `extract_doc.py` 明文密码清理 + 提供可用的 `lanhu_login` 自动登录（依赖上游/SSO 验证码情况）。

## 流程回写
| 发现 | 处理 | 落点 |
|------|------|------|
| 418 未被当作会话失效，原样报错且无重登入口 | 分类 401/403/418 + manual_action_required + 登录接口 | lanhu_provider / lanhu_evidence.py |
| 会话错误被"图片格式"兜底吞掉 → 虚假"已完成" | ai_service 会话错误透传 | ai_service.py |
| 前端用 stage=done 的"已完成"弱化失败 | 失败任务 stage 显示"已结束（失败）" | JobDetail.tsx |

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 6h / 实际 4h | 0/0/0/2 | 1 | 工具链 | 新 worktree 先装依赖；证据脚本先核对路由再断言 |

**技能使用**: `cameltv-agent-team` / `cameltv-bug-guard` / `cameltv-ui-conventions` / `vision`。
