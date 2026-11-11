# Batch 299 — Design / Dev

## 接口

```python
KINDS = 10 类
InterferenceSignal(kind, severity, evidence)
detect(payload: dict) -> list[InterferenceSignal]
InterferenceDetector().detect(payload)  # 薄封装
```

## 检测规则（阈值）

| kind | 触发 | critical |
|------|------|----------|
| cpu_throttle | throttled_seconds>0 或 usage≥95 | ≥5 / ≥98 |
| memory_pressure | available<256MB 或 oom>0 | <128 或 oom>0 |
| network_latency | p95>500ms 或 loss>1% | max≥2000 |
| dns_failure | failures>0 | ≥3 |
| disk_full | free<5% | <2% |
| process_crash | crash_count>0 | ≥2 |
| port_conflict | conflict 或 bind_errors>0 | — |
| dependency_5xx | 5xx_rate>5% 或 upstream>0 | >20% |
| clock_skew | |skew|>1000ms | >5000 |
| lock_contention | wait>1000ms 或 contention>0 | >5000 |

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-299-1 | 纯函数检测 | 满足“检测不改 Run 状态” |
| D-299-2 | 点路径读取 + 默认值 | payload 可增量扩展，缺字段不误报 |
| D-299-3 | severity 由阈值分级 | 便于后续告警/降噪 |
| D-299-4 | 不落库 | TA-023 只做信号；持久化随 observations 表 |

## 文件

- `app/aiqe/services/interference_service.py`
- `tests/test_aiqe_interference_detectors.py`（17 条）
