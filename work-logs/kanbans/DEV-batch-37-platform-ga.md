# DEV Kanban — Batch 37: 平台生产就绪

> **创建**: 2026-07-23 | **Executor**: Claude Code | **Workflow**: Agent Team

## 总览

| 维度 | 值 |
|------|-----|
| 目标 | 补齐 P0 阻断 + P1 严重缺口 + 联动 Phase 1 MVP |
| 总 Slice | 12 |
| 当前 Slice | 0 — 准备阶段 |
| 分支 | `feature/batch-37-platform-ga` |

---

## Phase 1: P0 阻断修复

### Slice 1: 音视频真实化
- [ ] Task 1.1: 后端 ffprobe 探测引擎 🔄
- [ ] Task 1.2: 前端音视频指标展示更新

### Slice 2: API 测试生产保护 + 请求快照
- [ ] Task 2.1: 环境标记模型 + API
- [ ] Task 2.2: API 请求/响应快照存储
- [ ] Task 2.3: API 任务取消真中断

### Slice 3: UI 自动化产物回看 + 异步执行
- [ ] Task 3.1: UI 产物静态文件服务
- [ ] Task 3.2: 前端产物查看器
- [ ] Task 3.3: UI 测试异步执行 + 环境注入

---

## Phase 2: P1 效率提升

### Slice 4: Swagger 导入
- [ ] Task 4.1: 后端 Swagger 解析器
- [ ] Task 4.2: Swagger → ApiTestCase 生成
- [ ] Task 4.3: 前端 Swagger 导入页面

### Slice 5: 批量执行 + 执行指派
- [ ] Task 5.1: 后端批量执行
- [ ] Task 5.2: 执行指派模型 + API
- [ ] Task 5.3: 前端批量执行 + 指派 UI

### Slice 6: 报告导出 + 趋势分析
- [ ] Task 6.1: 后端 PDF/Excel 导出
- [ ] Task 6.2: 多计划趋势分析
- [ ] Task 6.3: 前端报告导出按钮 + 趋势页面

### Slice 7: 用例评审流
- [ ] Task 7.1: 后端用例评审状态机
- [ ] Task 7.2: 前端评审界面

---

## Phase 3: 联动增强 Phase 1

### Slice 8: AiResultModal 三 Tab + source_req_id
- [ ] Task 8.1: 后端 AI 生成结果分类
- [ ] Task 8.2: 前端 AiResultModal Tab 切换

### Slice 9: 需求-API 映射 + 自动建计划
- [ ] Task 9.1: 需求-API 语义映射引擎
- [ ] Task 9.2: 导入后自动建测试计划

---

## Phase 4: P2 体验 + 工程债务

### Slice 10: P2 快速修复
- [ ] Task 10.1: 蓝湖原型配置化
- [ ] Task 10.2: 质量门禁初版
- [ ] Task 10.3: 版本历史查看

### Slice 11: 工程债务
- [ ] Task 11.1: npm audit 漏洞修复
- [ ] Task 11.2: Ruff 全规则清理

### Slice 12: 其他 P2
- [ ] Task 12.1: 验证码/SSO/找回密码
- [ ] Task 12.2: 自定义看板/仪表盘
- [ ] Task 12.3: 项目模板/归档/克隆

---

## 批次记录

| 日期 | 事件 | 详情 |
|------|------|------|
| 2026-07-23 | 开工 | Claude Code executor, Product/PM/Design 工件完成 |
