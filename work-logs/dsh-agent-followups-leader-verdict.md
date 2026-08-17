# DSH 测试 Agent 框架遗留收口 — Leader 判决

> 日期：2026-08-17 | 执行器：DeepSeek Harness | 分支：feature/dsh-agent-followups

## 判决：✅ APPROVED（C-A2/A3/A4 关闭；C-A1 部署期验收）

## 依据

1. **C-A4 缺陷回写闭环**：`POST /open/defects`（token 项目隔离 + 知识入库）+ MCP `submit_defect` + 3 后端测试 + 1 MCP 测试全绿
2. **C-A2 生产配置收口**：deploy/.env.example + docker-compose.yml 环境透传 + production.env.example 三处补 DSH 段（含 DSH_MODEL_POOL）
3. **C-A3 全流程冒烟**：需求→拓扑→用例→设计入库→触发执行→回读→缺陷回写→**知识检索命中缺陷/用例切片**（7 步全通）
4. **C-A1**：Dockerfile/requirements 已就绪，本地 Docker Desktop daemon 无法在 SYSTEM 会话初始化（需桌面授权）——转部署期验收，不阻塞合入
5. 自检：ruff ✅、后端相关域 71 ✅、MCP 17 ✅

## 流程回写

- C-A1 部署期验收清单：`docker build -t knowledge-mcp:latest knowledge-mcp` → `docker run -p 8110:8110 --env-file .env knowledge-mcp` → fastmcp Client 握手 17 工具
- 新增提醒：知识入库开关 `KNOWLEDGE_INGEST_ENABLED` 是缺陷/用例回流的前提，生产模板已默认开启

## 复盘卡

- **做得对**：C-A3 冒烟覆盖完整闭环（含知识回流验证），发现 ingest 开关依赖并在文档显式记录
- **教训**：Docker Desktop 在 SYSTEM 会话无法完成初始化——容器类验收应在用户会话或 CI 执行
