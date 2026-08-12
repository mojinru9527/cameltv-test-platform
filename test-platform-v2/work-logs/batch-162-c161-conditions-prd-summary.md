# Batch 162 — C161-1/2/3 三项遗留条件修复（PRD）

> **Product (🟦)** | Date: 2026-08-12 | Status: Draft | Mode: full（含 Schema 变更：调度 environment_id）

## 1. 问题陈述
Batch 161 生产复验后遗留 3 个 Leader 条件：
- **C161-1（P1）** 蓝湖自动登录无法完成：Railway 未配置 LANHU_USERNAME/LANHU_PASSWORD；且 Cookie 文件写在非持久卷 /data/lanhu，部署后丢失。pinned lanhu-mcp 子模块（3cfd2ef）已含 lanhu_login，登录链路代码已在。
- **C161-2（P2）** 含 API 用例的定时调度（15.0.0-每日上线回归）触发被环境预检拦截：test_schedule 无 environment_id，scheduler 执行 execute_all_cases 不传环境。
- **C161-3（P3）** 用例 surface 仍有 79 条「其他」：域名规则未覆盖 UGC统计指标(24)/虚拟货币(21)/聊天室(18)/比赛列表/体育数据-篮球/通知-比分变更/APP-版本更新/赛事/WEB-第三方社媒引导移除。

## 2. 成功指标
| 指标 | 基线 | 目标 |
|------|------|------|
| 蓝湖采集（配置凭据后） | 自动登录失败 | 配置 LANHU_USERNAME/PASSWORD 或粘贴 Cookie 后 #30 类任务成功；Cookie 跨部署保留 |
| 15.0.0 定时调度触发 | execution_failed（缺环境） | 绑定 Test5 环境后触发成功（405 条 skip 或执行） |
| surface「其他」 | 79 条 | 回填后 0 条 |

## 3. 非目标
- 不实现蓝湖验证码/风控绕过；自动登录最终成功依赖用户提供有效账号密码（Railway Variables）。
- 不改 execute_all_cases 语义；仅让调度透传环境。
- 不调整已入库用例内容（仅 surface 归类回填）。

## 4. 用户故事 + 验收
- As 运维, I want 粘贴的蓝湖 Cookie 跨部署保留, so that 采集不因重建丢失会话。验收：/app/storage 持久卷内存在 lanhu_cookie.txt，redeploy 后仍可读取。
- As 测试人员, I want 定时调度绑定执行环境, so that 含 API 用例的计划可定时回归。验收：新建/编辑调度可选环境；含 API 计划未选环境被拦截；触发时透传环境。
- As 测试人员, I want 16.0.0 用例端标识准确, so that 统计按端可信。验收：surface「其他」=0（复验）。

## 5. 技术考量
- C161-1：Dockerfile DATA_DIR /data/lanhu → /app/storage/lanhu-data（持久卷）；文档登记 Railway LANHU_USERNAME/PASSWORD 配置。
- C161-2：test_schedule 加 environment_id（Alembic 迁移）；ScheduleCreate/Update/Out 扩展；create/update 校验 API 计划必选环境；scheduler._execute_schedule 传 environment_id；前端表单环境下拉 + 列表展示。
- C161-3：surface 为派生值（无 DB 列），classify_case_surface 扩展域名规则 + 单测即修复展示/统计；不落库回填。

## 6. 上线计划
合入 + Railway 部署 → 用户补 LANHU_USERNAME/PASSWORD（或粘贴 Cookie）→ 生产复验（调度触发、采集、surface）。

## 7. 技能使用
cameltv-bug-guard（迁移/SSRF/Select）、cameltv-ui-conventions（表单）
