# 分环境灰度放量 SOP

> 目的: 新功能上线时按 Test → Staging → Production 逐级放量，控制风险。
> 适用: 所有 test-platform-v2 新功能和配置变更
> 最后更新: 2026-07-26

---

## 灰度放量模型

```
Test (开发环境)  →  Staging (预发布)  →  Production (生产)
  100% 流量           内部验证 24h         逐% 放量: 5%→25%→50%→100%
```

---

## 第一级: Test 环境

### 放量条件
- [ ] 后端 757+ 测试全部通过
- [ ] Alembic upgrade head 无错误
- [ ] 前端 typecheck + build 成功

### 验证清单
- [ ] 新功能 API 端点可达 (curl/Postman)
- [ ] 新功能 UI 页面可访问
- [ ] 核心回归: 用例→计划→API→UI→报告 链路无回归
- [ ] 无 console error / 500 错误

### 观测指标
| 指标 | 来源 | 观察窗口 |
|------|------|---------|
| 后端错误率 | app logs | 1h |
| API 响应时间 P95 | APM (如有) | 1h |
| 迁移执行状态 | Alembic | 单次 |

### 放量决策
- 无 P0/P1 缺陷 → 进入 Staging
- 出现 P0/P1 → 修复后重新 Test

---

## 第二级: Staging 环境

### 放量条件
- [ ] Test 环境验证通过（≥1h 无异常）
- [ ] Alembic upgrade + downgrade 双向验证通过

### 验证清单
- [ ] Tier 1 核心链路浏览器端逐页验收
- [ ] Wiki 同步覆盖率 ≥70%
- [ ] 图谱视图 200 节点 <3s
- [ ] 新功能 UI 在 Desktop + Tablet 分辨率可用

### 观测指标
| 指标 | 来源 | 观察窗口 |
|------|------|---------|
| 后端错误率 | Docker logs | 24h |
| DB 迁移状态 | Alembic current | 单次 |
| 前端性能 | Lighthouse (如有) | 单次 |

### 放量决策
- 24h 无 P0/P1 → 进入 Production 5%
- 出现 P1 → 修复后重新 Staging
- 出现 P0 → 立即回滚

---

## 第三级: Production 环境

### 5% 放量

| 操作 | 命令/方式 |
|------|----------|
| 部署新版本 | `docker compose -f docker-compose.prod.yml up -d backend` |
| 灰度 | 按项目/用户白名单启用新功能（通过 feature flag 或 config） |
| 监控 | 重点监控新功能端点的错误率和延迟 |

**观察窗口**: 4h
**成功门槛**: 错误率 <1%, P95 <基线 +20%

### 25% 放量

| 操作 | 方式 |
|------|------|
| 扩大范围 | 扩展到 25% 项目或用户 |

**观察窗口**: 24h
**成功门槛**: 无新增 P0/P1 缺陷

### 50% → 100% 放量

| 阶段 | 观察窗口 | 门槛 |
|------|---------|------|
| 50% | 24h | 用户反馈无新增 P0/P1 |
| 100% | 持续监控 48h | 回归缺陷率 < 上版本 |

---

## 回滚触发条件

| 严重级 | 条件 | 回滚方式 |
|--------|------|---------|
| P0 | 服务崩溃/数据丢失/安全漏洞 | **立即回滚**: `docker compose up -d` 恢复上一版本镜像 |
| P1 | 核心功能不可用 | **4h 内**: 回滚或 hotfix |
| P2 | 有替代路径 | 下次 release 修复 |

## 回滚步骤

```bash
# 1. 停止当前版本
docker compose -f docker-compose.prod.yml stop backend

# 2. 切换到上一版本镜像
# 编辑 docker-compose.prod.yml: image: cameltv-backend:v{prev}

# 3. 启动上一版本
docker compose -f docker-compose.prod.yml up -d backend

# 4. 验证
curl -s https://{prod-host}/api/v1/health | jq .

# 5. 通知团队
# → Slack/DingTalk 通知: "Production 已回滚至 v{prev}，原因: {reason}"
```

---

## 配置变更放量

对于 config.py 中的开关变更（如 `wiki_enabled`, `lanhu_mcp_enabled`），放量模型：

| 环境 | 动作 |
|------|------|
| Test | 先改为 `True`，跑全量测试 |
| Staging | 保持 `True` 24h，验证功能正常 |
| Production | 与代码部署同步，先 `False` → 验证 1h → `True` |
