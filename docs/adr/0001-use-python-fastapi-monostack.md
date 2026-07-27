---
title: "ADR-0001: Python FastAPI 纯单栈"
owner: "tech-lead"
last_reviewed: "2026-06-26"
status: "active"
expires: "2027-06-26"
tags: ["adr", "architecture", "python", "fastapi", "tech-stack"]
related: ["0002-sqlite-with-postgresql-upgrade-path.md", "0003-frontend-backend-physical-separation.md"]
---

# ADR-0001: 采用 Python FastAPI 纯单栈

## 状态

✅ 已采纳

## 日期

2025-12

## 背景

测试平台 v1 初期设计采用 Java Spring Boot（Web 后端）+ Python（CLI 工具）双栈架构。实践中发现：

- 双栈维护成本高——需要两套 CI/CD、两套依赖管理、两套编码规范
- 团队人力有限，同时维护 Java 和 Python 导致上下文切换频繁
- CLI 工具（环境探活、API 测试、流量抓取等）本身是 Python，Web 后端用 Java 意味着同一领域逻辑分散在两种语言中

v2 重构时，需要决定后端技术栈。

## 决策

采用 **纯 Python FastAPI** 作为唯一后端技术栈：
- Web 后端：FastAPI（高性能异步框架，自动生成 OpenAPI 文档）
- CLI 工具：保持 Python，复用相同的 Service 层
- ORM：SQLAlchemy 2.0
- 放弃 Java Spring Boot

## 后果

### 正面影响

- ✅ 统一技术栈，降低维护和招聘成本
- ✅ 前后端 TypeScript + Python 两种语言，上下文切换可控
- ✅ FastAPI 自动生成 OpenAPI，前后端契约由代码驱动
- ✅ CLI 工具和 Web 后端可共享核心逻辑（config_loader、http_client 等）

### 负面影响 / 权衡

- ⚠️ Java 生态在大型企业级系统更成熟（但当前规模不需要）
- ⚠️ Python GIL 可能成为性能瓶颈（目前未触发，可后期通过多 worker 缓解）
- ⚠️ 放弃了 Java 的强类型编译期检查优势（通过 mypy + Pydantic 部分弥补）

## 弃选方案

### 方案 A: Java Spring Boot + Python CLI

- 优点：Java 在后端系统成熟度高，Spring 生态完善
- 缺点：双栈维护成本，团队需同时掌握两种语言
- 放弃原因：团队规模小，双栈 ROI 低

### 方案 B: Go + Python CLI

- 优点：Go 性能好，部署简单
- 缺点：Go 在业务系统的 ORM/迁移/管理后台生态不如 Python/Java
- 放弃原因：业务系统用 Go 开发效率低于 FastAPI

## 关联

- 重构方案文档：[测试平台-前后端分离重构方案.md](../../测试平台-前后端分离重构方案.md)
- 相关 ADR: [ADR-0003](0003-frontend-backend-physical-separation.md)
