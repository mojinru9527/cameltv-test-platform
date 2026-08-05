# Batch 88 — Design Spec（C87-1/2/3 契约设计）

> **Design (🎨)** | Date: 2026-08-05 | Status: 就绪

## 0. 技术体系确认

- 前端：本批**无前端 UI 改动**（角色管理/通知配置/证据包页面均已存在），`cameltv-ui-conventions` 走查结论：不适用（无组件/样式/布局变更）。
- 后端：FastAPI + SQLAlchemy + Pydantic；RBAC 计算入口 `rbac_service.permission_codes/has_permission`；通知发送 `notify_service`；蓝湖链路 `services/external/lanhu_provider.py` + `services/lanhu_evidence/*`。
- 数据层：无 Schema 变更；变更集中于 seed 数据矩阵与 provider 逻辑。

## 1. RBAC 权限矩阵契约（C87-3 设计产出）

### 1.1 角色语义（不变）

| 角色 | data_scope | 权限语义 | 本批变化 |
|------|-----------|---------|---------|
| `admin` | global | `*`（全部权限，超管） | 不变 |
| `tester` | project | 项目内测试工作权限；不授予系统/项目管理/生产操作 | **扩充矩阵** |

### 1.2 tester 权限矩阵（新增/保留对照）

| 模块 | 保留（已有） | 本批新增 | 明确不授予 |
|------|------------|---------|-----------|
| 用例 testcase | — | `testcase:list/detail/create/update/delete/export` | — |
| 测试计划 testplan | — | `testplan:list/detail/create/update/delete/execute` | — |
| 报告 report | — | `report:list/detail/create` | `report:delete`（留管理员） |
| 定时任务 schedule | `schedule:list` | `schedule:create/update/delete/trigger` | — |
| 缺陷 defect | — | `defect:list/detail/create/update` | `defect:delete`（留管理员） |
| 需求 requirement | — | `requirement:upload/generate/import` | — |
| 数据集 dataset | — | `dataset:list/create/update/delete` | — |
| 用例评审 review | — | `review:submit/approve` | — |
| 版本测试任务 mission | — | `mission:list/detail/create/update/log` | `mission:delete`、`mission:generate`（AI 生成留管理员/按需） |
| 通知 notify | — | `notify:list/manage` | — |
| API/UI/专项 | `apitest:execute/view/import/generate/task/asset_manage` | `uitest:list/detail/create/update/delete/trigger`、`avcheck:list/detail/create/delete/trigger` | `*_prod`（`apitest:execute_prod`、`uitest:trigger_prod`） |
| 知识/Wiki/Agent | `knowledge:view`、`agent:view/list`、`wiki:view/diff` | — | `knowledge:manage/approve`、`wiki:manage/approve`、`agent:run/admin`、`ai_artifact:import` |
| 蓝湖证据包 | `lanhu_evidence:view/run` | — | `lanhu_evidence:import/review`（导入/审核留管理员，避免证据直入） |
| 系统/项目管理/Token | — | — | `system:*`、`project:*`、`token:list/manage`、`release:view`、`integration:sync_prod`、`perftest:report`（保留 `perftest:*` 其余） |

> 设计决策：tester 的 `lanhu_evidence:run` 保留（可发起采集），但 `import` 需管理员（`lanhu_evidence:import`）——避免普通成员把未审证据直接写入知识库；这与 lanhu_evidence.py 的运行时二次校验一致。
> `schedule:delete` 与 `defect:delete` 设计差异说明：定时任务为 tester 自建可删；缺陷删除涉审计语义，保留管理员。

### 1.3 前端菜单联动

菜单树由后端 `menu_service.menu_tree(db, current.permissions)` 下发，新增按钮权限码自动使前端按钮可用，无需改前端。

## 2. SMTP 配置契约（C87-2 设计产出）

### 2.1 配置项

| 配置 | 值（运行环境） | 说明 |
|------|--------------|------|
| `SMTP_HOST` | `smtp.qq.com` | QQ 企业/个人邮箱 SMTP |
| `SMTP_PORT` | `587` | STARTTLS |
| `SMTP_USER` | `2602997810@qq.com` | 发件账号 |
| `SMTP_PASSWORD` | （deploy/.env 已登记，掩码） | 仅存 gitignore 的 .env |
| `SMTP_FROM` | `2602997810@qq.com` | **修正**：deploy/.env 现值为 `pop.qq.com`（疑似误填），QQ 要求 From=登录邮箱 |
| `SMTP_USE_TLS` | `true` | STARTTLS |
| `SMTP_VERIFY_CERT` | `true` | 证书校验保持开启（P1-S5a 安全基线） |

### 2.2 生效路径

`notify_service._dispatch_email` 读取 `settings.smtp_*` → `_send_email` → `_sync_send_email`（smtplib + starttls + login + send_message）。收件人为通知渠道 `webhook_url` 字段逗号分隔的邮箱列表（现有语义复用，无新端点）。

### 2.3 反向用例

`SMTP_HOST` 为空 → `_dispatch_email` 返回 `("SMTP not configured", 0)` 且不打坏 webhook 渠道（现有逻辑，回归验证）。

## 3. 蓝湖项目级链接流程设计（C87-1 设计产出）

### 3.1 现状与目标流程

```text
现状: 项目级 URL（tid+pid，无 docId）→ get_lanhu_pages_for_evidence → 报「缺少 docId」
目标: 项目级 URL
  → 共享 helper resolve_doc_ids_for_project(url, extractor)
      GET https://lanhuapp.com/api/project/images?project_id={pid}&team_id={tid}&dds_status=1&position=1&show_cb_src=1&comment=1
      data.code == "00000" → data.data.images[]（id + name）
  → 追加 docId → 按文档建证据包任务（每个文档一个 job，source_url 带 docId）
  → 复用现有 job_runner：发现页面 → 截图 → OCR → 质量门禁 → 导入
```

### 3.2 接口/纯函数契约

| 函数 | 签名 | 行为 |
|------|------|------|
| `lanhu_provider.resolve_doc_ids_for_project(url, extractor)`（新增） | `-> list[dict]` | 项目 URL 时调 `/api/project/images` 返回 `[{id, name}]`；失败抛 ValueError（含认证/权限分类提示） |
| `lanhu_provider.get_lanhu_pages_for_evidence(url)`（改造） | 无 docId 时自动 resolve 并取首个文档 | 保持返回 `{status, resource_dir, document_name, pages}`；无文档时 `status=failed, error="项目内未发现设计文档"` |
| `page_discovery.parse_lanhu_url(url)`（不变） | tid/pid/docId/versionId/pageId | hash query 解析已支持 |

### 3.3 错误/边界状态

| 场景 | 行为 |
|------|------|
| 项目内 0 个文档 | `status=failed`，任务不进入截图阶段 |
| 认证失败 | 复用现有 auth_error 重试（auto-login），失败报「认证失败，请更新 Cookie」 |
| 下载受限（limited/manual_action_required） | `LanhuManualActionRequired` → 任务 failed + 人工处理提示（现有门禁） |
| 截图 0 页 | 任务 failed（现有 job_runner 逻辑） |
| OCR 全空但截图成功 | `success_with_warnings`，导入被质量门禁阻止（import_ready=false），人工审核后可豁免 |

## 4. 设计 QA 走查发现

### 🟠 P2-01 `SMTP_FROM` 疑似误填
`deploy/.env`（gitignore）中 `SMTP_FROM=pop.qq.com` 非邮箱地址，QQ SMTP 会拒绝 From 校验。
→ **处理**：本批在 `backend/.env` 使用 `SMTP_FROM=2602997810@qq.com`；同步修正 `deploy/.env.example` 注释示例；`deploy/.env` 属本机配置，Leader 与用户确认后由用户/运维修正（不 commit 凭据）。

### 🟡 P2-02 OCR 命令路径绑定控制仓库
`LANHU_OCR_COMMAND` 指向 `F:/CamelTv/test-platform/.venv/Scripts/python.exe` 与 `F:/CamelTv/test-platform-v2/...`（控制仓库路径），worktree 运行会失效。
→ **处理**：Slice 0 将命令改为 worktree 内可执行路径（venv python + `test-platform-v2/backend/scripts/ocr_paddle.py`），并保持 gitignore。

### 🟡 P3-01 项目多文档 fan-out 边界
一个蓝湖项目含多份设计稿时，证据包按文档逐个建任务（先 resolve 全量 docId 列表），**不做**自动批量 fan-out，避免任务风暴与重 OCR 成本；QA 记录发现文档数与已处理数。

## 5. 设计签核

结论：**通过（有条件）** — P2-01/P2-02 为配置落地项，随 Slice 0 处理；无 UI/组件变更，无阻断项。
