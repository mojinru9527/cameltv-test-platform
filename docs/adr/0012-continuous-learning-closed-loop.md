# ADR-0012: 持续学习闭环架构

**状态**: Accepted
**日期**: 2026-07-09
**决策者**: Dev 部门
**关联**: [ADR-0009](0009-knowledge-center-agent-continuous-learning.md), [ADR-0010](0010-knowledge-vector-embedding-hybrid-retrieval.md)

---

## 背景

M5（自动触发）+ M6（迭代知识包）构成知识库持续学习闭环的最后两个里程碑。核心问题：

1. **什么时候该跑 Agent？** 知识源变更后，需要自动检测并触发对应类型的 Agent 重新分析
2. **这个迭代学到了什么？** 每个迭代周期结束时，需要沉淀知识快照，支持跨迭代对比和趋势洞察
3. **变更影响了什么？** 需要基于知识图谱预测 API 变更的回归波及范围

---

## 决策

### D1: 触发检测 — 内容哈希对比

**方案**: 使用 SHA256 内容哈希（`content_hash`）检测知识源变更，而非时间戳。

**理由**:
- 时间戳不可靠：同一文档重复保存（内容未变）会误触发
- 哈希去重：同一内容多次导入只触发一次变更检测
- 哈希值存储在 `knowledge_source.metadata_json` 中，不新增字段

**备选方案**: 
- `updated_at` 时间戳对比 → 否决：重复保存误触发
- 文件系统 `mtime` → 否决：跨环境不可靠

### D2: 触发策略 — 可配置规则

**方案**: 基于事件类型到 Agent 类型的映射规则，支持项目级开关。

```python
TRIGGER_RULES = {
    "requirement_updated": ["requirement_analysis", "impact_analysis"],
    "api_schema_changed":   ["impact_analysis", "case_generation"],
    "new_defect":           ["failure_analysis"],
    "execution_failure":    ["failure_analysis"],
}
```

**理由**:
- 解耦：事件类型与 Agent 类型独立演进
- 可配置：规则通过 API 暴露，后续可支持 UI 编辑
- 默认 OFF：`knowledge_graph_enabled` 作为总开关，防止噪声触发

**备选方案**:
- 硬编码触发逻辑 → 否决：不可扩展
- 全自动触发（无开关）→ 否决：噪声过多

### D3: 防抖 — 300 秒窗口

**方案**: 同一 `source_id:agent_type` 在 300 秒内不重复触发。

**理由**:
- 防止批量导入时重复触发（一次导入 100 个接口不应触发 100 次 Agent）
- 300 秒窗口覆盖典型的批量操作时间窗
- 内存级去重（`_last_trigger` dict），重启后自动清除

**备选方案**:
- 5 分钟固定间隔 → 否决：不够灵活
- DB 持久化防抖 → 否决：过度设计，内存够用

### D4: 任务队列 — 内存 + DB 持久化

**方案**: 引入 `agent_queue_item` 表持久化队列，后台线程轮询调度。

**设计要点**:
- 每个项目最多 2 个 Agent 并发执行
- 优先级：手动触发 (10) > 自动触发 (0)
- 失败自动重试 1 次（间隔 30 秒）
- pending 任务可手动取消

**理由**:
- 不依赖 Redis/Celery：初版数据规模下，DB+线程够用
- 持久化：服务重启不丢任务
- 向后兼容：现有 `POST /agents/run/{type}` 自动入队

**备选方案**:
- Celery + Redis → 否决：引入额外运维复杂度，M5 阶段不值得
- 纯内存队列 → 否决：重启丢任务不可接受

### D5: 迭代知识包 — 快照模式

**方案**: 引入 `knowledge_iteration` + `knowledge_snapshot` 两张表，关闭迭代时自动捕获快照。

**快照类型**:
- `entity`: 按 entity_type 分组计数 + 平均置信度
- `relation`: 按 relation_type 分组计数 + 待审核数
- `chunk`: 按 chunk_type 分组计数
- `stats`: 综合统计（知识源数量 + 采集时间）

**理由**:
- 仅存统计摘要，不存全量数据（避免膨胀）
- 关闭时自动创建，幂等（覆盖已有快照）
- 跨迭代对比通过 SQL 聚合 + JSON 比较实现，不引入时序数据库

**备选方案**:
- 全量数据快照 → 否决：存储膨胀
- 时序数据库（InfluxDB）→ 否决：过度设计

### D6: 回归预测 — 图谱驱动 + 关键词降级

**方案**: 基于 M3 知识图谱的 `affects` 关系 + chunk 关键词匹配计算风险分数。

**风险公式**:
```
risk_score = min(defect_count/5, 0.6) + min(related_chunks/20, 0.2) + min(suggested_tests/10, 0.2)
```

**理由**:
- 图谱优先：利用已有的 entity/relation 数据
- 降级策略：无图谱数据时用 chunk 关键词匹配兜底
- 置信度标注：低分项不阻塞流程

**备选方案**:
- LLM 驱动预测 → 否决：延迟高、成本高、不可解释
- 纯统计回归 → 否决：冷启动无数据时完全失效

---

## 后果

### 正面
- 知识库从"被动存储"进化为"主动触发 + 持续沉淀"
- 迭代快照提供可量化的知识增长度量
- 回归预测降低变更风险，提高测试效率
- 队列机制解耦了触发和执行，提高了系统稳定性

### 负面
- 引入 3 张新表（agent_queue_item, knowledge_iteration, knowledge_snapshot）
- 后台线程增加运行时复杂度
- 快照仅存摘要，无法回溯详细变更历史

### 风险缓解
- 自动触发默认 OFF，需要显式开启 `knowledge_graph_enabled`
- 防抖 + 并发限制防止资源耗尽
- 快照幂等覆盖，不产生重复数据

---

## 参考

- [ADR-0009: 知识中心 Agent 持续学习能力](0009-knowledge-center-agent-continuous-learning.md)
- [ADR-0010: 向量化与混合检索](0010-knowledge-vector-embedding-hybrid-retrieval.md)
- [DEV-batch-15 看板](../../work-logs/kanbans/DEV-batch-15-rag-m5-m6-continuous-learning.md)
