# Batch 37 — Design Spec
> **Design (🎨)** | Date: 2026-07-23 | Status: 就绪

## 0. 技术体系确认

- **前端**: React 18 + TypeScript + shadcn/ui (Radix + Tailwind + CVA)
- **后端**: Python FastAPI + SQLAlchemy + SQLite WAL (可升级 PostgreSQL)
- **图表**: Recharts (已在工作台使用)
- **新增依赖**: `reportlab` (PDF), `openpyxl` (Excel), `prance` (Swagger 解析)
- **系统依赖**: `ffprobe` (FFmpeg 包), Playwright (已有)
- **Token 体系**: Tailwind 语义类（`bg-muted` / `text-muted-foreground` / `border` / `variant`）

---

## 1. 架构决策

### 1.1 ffprobe 音视频探测

```
┌─────────────┐     ┌──────────────────┐     ┌──────────┐
│  Frontend    │────▶│  POST /special   │────▶│ av_check │
│  /special    │     │  /check-stream   │     │ _service │
└─────────────┘     └──────────────────┘     └────┬─────┘
                                                   │
                                          subprocess.Popen
                                                   │
                                          ┌────────▼─────┐
                                          │  ffprobe      │
                                          │  -v quiet     │
                                          │  -print_format│
                                          │  json         │
                                          │  -show_format │
                                          │  -show_streams│
                                          │  {stream_url} │
                                          └──────────────┘
```

**决策**: 使用 `asyncio.create_subprocess_exec` 异步调用 ffprobe，解析 JSON 输出。不引入额外 Python 绑定库——直接用命令行是最稳定、最广泛兼容的方式。

**超时处理**: `asyncio.wait_for(proc.wait(), timeout=configurable)`，默认 30s。

**输出解析**:
```python
# ffprobe JSON 输出 → AvCheckResult
{
  "startup_latency_ms": ... ,   # format.start_time * 1000 (从 probing 时间推算)
  "bitrate_kbps": int(format.bit_rate / 1000),
  "fps": eval(stream.r_frame_rate),
  "resolution": f"{stream.width}x{stream.height}",
  "codec": stream.codec_name,
  "raw_output": { ... }          # 完整 ffprobe JSON
}
```

### 1.2 API 生产环境保护

```
执行 API 测试
    │
    ▼
获取目标 Environment
    │
    ▼
env_type == "production" ?
    │
    ├── YES ──▶ 检查 confirm_production 参数
    │              │
    │              ├── false/缺失 ──▶ 409 Conflict
    │              │                 {"error": "production_env_confirm_required",
    │              │                  "env_name": "...",
    │              │                  "message": "此环境标记为生产环境..."}
    │              │
    │              └── true ──▶ 继续执行 + 日志记录 "production_api_test_executed"
    │
    └── NO ───▶ 直接执行
```

**决策**: 不阻止生产环境执行（测试团队可能有需要在生产做冒烟测试），但必须通过显式参数确认。409 响应驱动前端弹出二次确认对话框。

### 1.3 UI 产物静态文件服务

```
Playwright 执行
    │
    ▼
产物保存到: artifacts/uitest/{execution_id}/
    ├── screenshot-{step}.png
    ├── video.webm
    └── trace.zip
    │
    ▼
GET /api/v1/uitest/artifacts/{execution_id}/{filename}
    │
    ▼
后端读取文件 → StreamingResponse(media_type=...)
```

**决策**: 产物通过 API 端点提供而非直接静态文件挂载——需要鉴权（验证用户对 execution 的访问权限）。不引入 nginx 静态服务（保持部署简单）。

### 1.4 Swagger 导入架构

```
上传 Swagger 文件
    │
    ▼
prance 解析 (OpenAPI 2.0/3.0 → 统一 dict)
    │
    ▼
遍历 paths → 提取 operations
    │
    ▼
存入 swagger_imports 表
    │
    ▼
返回 paths 列表供前端展示
    │
    ▼
用户勾选 → POST /swagger/generate-cases
    │
    ▼
为每个选中的 operation 创建 ApiTestCase
    ├── api_method: operation.method
    ├── api_endpoint: operation.path
    ├── request_body_schema: operation.requestBody (JSON)
    ├── response_schema: operation.responses (JSON)
    ├── swagger_operation_id: operation.operationId
    └── assertions: [{type: "status_code", expected: "2xx"}, ...]
```

**决策**: 两步式流程——先解析预览，再选择生成。避免一键导入产生大量垃圾用例。

### 1.5 批量执行架构

```
POST /api/v1/test-plans/{id}/execute-all
    │
    ▼
获取 plan-cases 列表 (按 order_index 排序)
    │
    ▼
Semaphore(concurrency) 控制并发
    │
    ▼
asyncio.as_completed() 逐个执行
    │  ├── 执行 case → 记录结果
    │  ├── 检查 cancel_flag → 中断
    │  └── 推送进度到 WebSocket/轮询状态
    │
    ▼
返回汇总: {total, passed, failed, skipped, blocked, duration}
```

**决策**: 使用 `asyncio.Semaphore` 控制并发数，避免对目标服务造成压力。通过 `cancel_event` (asyncio.Event) 实现可中断。

### 1.6 报告导出架构

```
报告数据
    │
    ├──▶ PDF: ReportLab Platypus
    │      ├── 封面: 标题/项目/日期/通过率
    │      ├── 统计摘要: 表格
    │      ├── 图表: matplotlib → 临时 PNG → 嵌入 PDF
    │      └── 用例明细: 分页表格
    │
    └──▶ Excel: openpyxl
           ├── Sheet 1: 用例明细
           ├── Sheet 2: 缺陷明细
           └── Sheet 3: 统计摘要
```

**决策**: PDF 图表先用 matplotlib 生成静态 PNG 嵌入（ReportLab 原生图表能力弱）。Excel 使用 openpyxl（支持 .xlsx 格式）。

### 1.7 用例评审状态机

```
         AI 生成
            │
            ▼
      ┌─ pending_review ──┐
      │                    │
   approve             reject (+ 评审意见)
      │                    │
      ▼                    ▼
   active              draft (可重新提交)
      │                    │
      ▼                    ▼
   可加入计划          pending_review (重新评审)
```

**决策**: 简化为 3 态（pending_review → active/rejected-draft），避免过度设计。AI 生成的用例默认 pending_review；手工创建的默认 active。

---

## 2. 数据模型变更

### 2.1 Environment 增加 env_type

```python
# app/models/environment.py
env_type = Column(String(16), default="test", nullable=False)
# 可选值: "production", "staging", "test"
```

### 2.2 SwaggerImport 新表

```python
# app/models/swagger_import.py (新建)
class SwaggerImport(Base):
    __tablename__ = "swagger_imports"
    id = Column(Integer, primary_key=True)
    filename = Column(String(255))
    version = Column(String(16))        # "2.0" / "3.0"
    title = Column(String(255))
    description = Column(Text)
    raw_content = Column(JSON)          # 解析后的完整 spec
    paths_count = Column(Integer)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())
```

### 2.3 TestCase 增加字段

```python
# app/models/test_case.py 增加
review_status = Column(String(16), default="active")
# 可选值: "pending_review", "active", "draft"
reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
review_comment = Column(Text, nullable=True)
reviewed_at = Column(DateTime, nullable=True)

swagger_operation_id = Column(String(255), nullable=True)
swagger_path = Column(String(512), nullable=True)
swagger_method = Column(String(16), nullable=True)

source_req_id = Column(Integer, nullable=True)  # 关联 requirement_analysis.id
version = Column(Integer, default=1)             # 用例版本号
```

### 2.4 TestPlanCase 增加指派字段

```python
# app/models/test_plan.py TestPlanCase 增加
assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
due_date = Column(DateTime, nullable=True)
```

### 2.5 ExecutionResult 快照字段

```python
# 已有 execution_result (JSON) 字段增强
{
  "request_snapshot": {
    "method": "GET",
    "url": "https://...",
    "headers": {...},
    "body": "..."
  },
  "response_snapshot": {
    "status_code": 200,
    "headers": {...},
    "body": "...",
    "timing_ms": 234
  }
}
```

### 2.6 用例版本历史表

```python
# app/models/test_case.py (新建)
class TestCaseVersion(Base):
    __tablename__ = "test_case_versions"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("test_cases.id"))
    version = Column(Integer)
    title = Column(String(500))
    steps = Column(JSON)
    expected_result = Column(Text)
    changed_by = Column(Integer, ForeignKey("users.id"))
    changed_at = Column(DateTime, default=func.now())
    change_summary = Column(String(255))
```

---

## 3. API 契约

### 3.1 新增端点一览

| 方法 | 路径 | 说明 | Phase |
|------|------|------|-------|
| POST | `/api/v1/special/check-stream` | ffprobe 真实流探测 | P1 |
| GET | `/api/v1/apitest/swagger/import` | Swagger 文件上传解析 | P2 |
| POST | `/api/v1/apitest/swagger/{id}/generate-cases` | 生成接口用例 | P2 |
| GET | `/api/v1/uitest/artifacts/{exec_id}/{filename}` | 产物文件访问 | P1 |
| POST | `/api/v1/test-plans/{id}/execute-all` | 批量执行 | P2 |
| PUT | `/api/v1/test-plans/{id}/cases/{cid}/assign` | 执行指派 | P2 |
| GET | `/api/v1/reports/{id}/export/pdf` | PDF 导出 | P2 |
| GET | `/api/v1/reports/{id}/export/excel` | Excel 导出 | P2 |
| GET | `/api/v1/reports/trends` | 趋势数据 | P2 |
| POST | `/api/v1/testcases/{id}/review` | 用例评审 | P2 |
| POST | `/api/v1/requirements/{id}/map-swagger` | 需求-Swagger 映射 | P3 |
| POST | `/api/v1/requirements/{id}/import-with-plan` | 导入+建计划 | P3 |

### 3.2 关键端点详细设计

#### POST /api/v1/apitest/swagger/import

```
Request: multipart/form-data { file: Swagger JSON/YAML }
Response 200:
{
  "id": 1,
  "filename": "camel1tv-api.json",
  "version": "3.0.1",
  "title": "CamelTv API",
  "paths": [
    {
      "path": "/api/v1/matches",
      "method": "get",
      "summary": "获取赛事列表",
      "tags": ["Matches"],
      "parameters": [...],
      "request_body_schema": null,
      "response_schema": {...}
    },
    ...
  ],
  "paths_count": 42
}
```

#### POST /api/v1/special/check-stream

```
Request:
{
  "stream_urls": ["https://cdn.camel1.tv/live/channel1.m3u8"],
  "timeout_seconds": 30
}
Response 200:
{
  "results": [
    {
      "stream_url": "...",
      "status": "success",         // success | timeout | error
      "startup_latency_ms": 1234,
      "bitrate_kbps": 2500,
      "fps": 30,
      "resolution": "1920x1080",
      "codec": "h264",
      "raw_ffprobe": { ... }
    }
  ]
}
```

#### GET /api/v1/reports/{id}/export/pdf

```
Response 200: application/pdf (binary)
Content-Disposition: attachment; filename="report-{id}-{date}.pdf"
```

---

## 4. 前端组件设计

### 4.1 AiResultModal Tab 改造

```
┌──────────────────────────────────────────────┐
│  AI 用例生成结果                     [×]      │
├──────────────────────────────────────────────┤
│  [功能用例 12] │ [接口用例 5] │ [UI回归建议 8] │
├──────────────────────────────────────────────┤
│  ┌──────────────────────────────────────┐    │
│  │ ☑ 全部选中                  批量操作  │    │
│  │──────────────────────────────────────│    │
│  │ ☑ TC-001  用户登录功能验证    P0     │    │
│  │ ☑ TC-002  赛事列表展示验证    P0     │    │
│  │ ☐ TC-003  直播播放器功能验证  P1     │    │
│  │ ...                                  │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  [☑ 导入后创建测试计划]    [导入选中 (10)]    │
└──────────────────────────────────────────────┘
```

- 三 Tab 使用 shadcn/ui `<Tabs>` 组件
- "接口用例" Tab 若无 Swagger 数据：Empty 态 + "上传 Swagger 文档以生成接口用例"按钮
- "UI 回归建议" Tab 若无 release-bundle 数据：Empty 态 + 引导说明

### 4.2 Swagger 导入页面

```
┌──────────────────────────────────────────────┐
│  ← 返回    Swagger 导入                       │
├──────────────────────────────────────────────┤
│  ┌──────────────────────────────────────┐    │
│  │      📎 拖拽或点击上传 Swagger 文件      │    │
│  │      支持 JSON / YAML 格式             │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  解析结果: camel1tv-api.json (OpenAPI 3.0.1) │
│  共 42 个接口                                │
│  ┌──────────────────────────────────────┐    │
│  │ Tag 筛选: [All] [Matches] [Users]     │    │
│  │──────────────────────────────────────│    │
│  │ ☑ GET   /api/v1/matches     赛事列表   │    │
│  │ ☑ GET   /api/v1/matches/{id} 赛事详情 │    │
│  │ ☐ POST  /api/v1/matches     创建赛事   │    │
│  │ ...                                  │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  已选 35/42         [取消]  [生成接口用例]     │
└──────────────────────────────────────────────┘
```

### 4.3 产物查看器组件

```
┌──────────────────────────────────────────────┐
│  UI 测试执行结果                              │
├──────────────────────────────────────────────┤
│  状态: ✅ 通过    耗时: 45s                   │
│                                              │
│  📸 截图                                     │
│  ┌──────┐ ┌──────┐ ┌──────┐                │
│  │ step1│ │ step2│ │ step3│                │
│  │      │ │      │ │      │                │
│  └──────┘ └──────┘ └──────┘                │
│  点击放大                                    │
│                                              │
│  🎬 视频                                     │
│  ▶ ━━━━━━━━━━○──────── 0:45                │
│                                              │
│  🔍 Trace                                    │
│  [下载 trace.zip] [用 Trace Viewer 打开]      │
└──────────────────────────────────────────────┘
```

- 截图使用 shadcn/ui `<Dialog>` 放大查看
- 视频使用原生 `<video>` 标签
- trace 提供下载 + `npx playwright show-trace` 命令行引导

### 4.4 批量执行进度

```
┌──────────────────────────────────────────────┐
│  批量执行中...                                │
├──────────────────────────────────────────────┤
│  ████████████░░░░░░░░ 24/50 (48%)            │
│  ✅ 20  ❌ 3  ⏭ 1  ⏸ 0                     │
│                                              │
│  当前: TC-USER-003 用户注册验证               │
│  ──────────────────────────────────────       │
│  TC-USER-001  登录验证           ✅ 0.5s     │
│  TC-USER-002  登出验证           ✅ 0.3s     │
│  TC-USER-003  注册验证           🔄 执行中   │
│  TC-MATCH-001 赛事列表           ⏳ 等待中   │
│  ...                                         │
│                                              │
│  [取消执行]                                   │
└──────────────────────────────────────────────┘
```

---

## 5. 状态设计核对

### 5.1 各组件四态

| 组件 | Loading | Empty | Error | 未启用 |
|------|---------|-------|-------|--------|
| 音视频探测结果 | Skeleton 卡片 + "探测中..." | "尚未执行探测" | "ffprobe 不可用，请检查服务端安装" | 功能开关关闭 |
| Swagger 导入 | 上传进度条 | 上传区域引导 | "解析失败: 第X行 字段Y缺失" | — |
| 产物查看器 | 图片骨架屏 | "本次执行未产生产物" | "产物文件已过期或损坏" | — |
| 批量执行 | 进度条 + 动画 | "无待执行用例" | "执行中断: 连接超时" | — |
| 报告导出 | 生成中 spinner | — | "PDF 生成失败，请重试" | — |
| 用例评审 | 列表 Skeleton | "暂无需评审的用例" | — | — |
| AiResultModal Tab | Tab 内容 Skeleton | "此类型暂无用例" + 引导 | — | — |

### 5.2 环境确认对话框

```
┌──────────────────────────────────────┐
│  ⚠️ 生产环境确认                      │
├──────────────────────────────────────┤
│                                      │
│  目标环境 "CamelTv生产环境" 已标记为   │
│  生产环境 (production)。              │
│                                      │
│  执行 API 测试可能影响线上服务。       │
│  确认要继续吗？                       │
│                                      │
│  [取消]        [我已知晓，确认执行]    │
└──────────────────────────────────────┘
```

---

## 6. 设计 QA 走查（已有前端的反向回填）

> ⚠️ 以下为基于现有平台 UI 模式的推断，实际开发中需逐项确认。

### 🟡 P2-1 AiResultModal 内容溢出
现有 Modal 为单列表展示所有用例。新增三 Tab 后需验证内容区域高度，超长时启用 `overflow-y-auto`。

### 🟡 P2-2 批量执行按钮位置
建议放在测试计划详情页顶部操作栏，与"编辑计划""添加用例"同级。使用 `variant="default"` 主按钮样式。

---

## 7. 设计签核

**结论**: 就绪。技术方案可行，数据模型变更最小化，API 契约清晰，前端组件遵循现有 shadcn/ui 模式。

**待确认**:
1. 音视频是否需要鉴权直播流支持（需 Product 确认）
2. PDF 报告模板是否需要品牌 logo/页眉页脚（需 Product 确认）
3. trace 在线查看是否用 Playwright Trace Viewer 在线版还是仅下载（需技术评估）
