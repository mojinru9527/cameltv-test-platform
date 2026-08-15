---
title: "ADR-0020: OS 级沙箱（seccomp/nsjail）部署层评估结论"
owner: "tech-lead"
last_reviewed: "2026-08-16"
status: "active"
expires: "2027-02-16"
tags: ["adr", "security", "sandbox", "dsh", "deployment"]
related: ["0018-dsh-harness-integration.md", "0017-test5-runner-network-isolation.md"]
---

# ADR-0020: OS 级沙箱（seccomp/nsjail）部署层评估结论

## 状态

✅ 已采纳（评估结论：现状不引入 OS 级沙箱；自托管裸机部署时触发重新评估）

## 日期

2026-08-16

## 背景

Batch 184 完成 DSH 沙箱安全加固（C172-1/2 关闭）：任务级隔离工作区 `ws-{uuid}`、
全局并发闸门 `DSH_MAX_CONCURRENT`、任务文本配额 `DSH_MAX_TASK_CHARS`、
python-sdk 环境变量互斥锁。这些属于**进程内（应用层）隔离与配额**。

C184-1 提出后续评估：是否在**部署层**追加 OS 级沙箱（seccomp / nsjail / bubblewrap），
为「生产 Railway 容器 = 隔离单元」之外的场景（如自托管裸机直接运行 DSH）做准备。
本 ADR 记录该评估的结论与触发条件，关闭 C184-1。

## 决策

1. **现状不引入 OS 级沙箱**：生产部署以 Railway 容器为隔离单元（容器运行时提供
   cgroups + namespaces 的内核级资源与命名空间隔离），平台进程内隔离（Batch 184）
   已收敛资源滥用面；在容器内再叠加 nsjail/bubblewrap 不消除内核共享面，
   却引入 setuid/SUID、glibc 依赖与调试复杂度，收益不成比例。
2. **隔离模型分层（明确边界）**：
   - **L1 进程内（已落地，Batch 184）**：workspace 隔离 `ws-{uuid}`、并发闸门、
     任务字符配额、python-sdk env 锁——防「任务之间互相干扰/滥用平台资源」；
   - **L2 容器级（生产现状）**：Railway 容器为最小部署单元，DSH 子进程与平台
     服务同容器运行，容器本身即隔离边界；
   - **L3 OS 级（未启用，登记触发条件）**：seccomp-bpf syscall 过滤 /
     nsjail / bubblewrap 用户态沙箱。
3. **触发条件（自托管裸机部署时）**：若未来 DSH 不经容器运行时直接部署于
   自托管裸机（无 L2 隔离），必须重新评估并实施 L3：
   - 首选 **bubblewrap**（无需 root 的 setuid 助手、namespace+seccomp 组合，
     与 `deepseek-harness` 的 node/python-sdk 运行方式兼容）；
   - 备选 **nsjail**（强隔离但需编译/glibc 对齐）；
   - 部署形态决策时登记新 C 条件并补充安全回归。
4. **生产 DSH 开关不变**：`DSH_ENABLED` 生产保持 `false`；启用为独立部署决策，
   须先满足 L2 或 L3 隔离并走 release-control 审批（ADR-0015）。

## 后果

### 正面影响

- ✅ 安全模型边界清晰：应用层防滥用（L1）+ 容器层防逃逸扩散（L2）已覆盖
  当前部署形态；评估结论可追溯（C184-1 关闭证据）。
- ✅ 避免为收益不成比例的加固引入运维负担：不新增 setuid 二进制、
  不引入 glibc 版本对齐问题、不改变调试与故障排查路径。
- ✅ 触发条件明确：自托管裸机部署是唯一需要 L3 的形态，届时按决策 3 执行。

### 负面影响 / 权衡

- ⚠️ 自托管裸机形态下存在已登记的安全敞口（无 L2）：由触发条件保证不静默出现
  ——任何裸机部署 DSH 的行为必须先完成 L3 评估与实施。
- ⚠️ 容器内共享内核：L1/L2 不防御宿主内核漏洞（容器逃逸面）；该风险
  Railway 托管侧承担，自托管时归入 L3 评估范围。
- ⚠️ 进程内隔离（L1）依赖应用代码正确性：后续 DSH 能力扩展（新工具/新运行时）
  需同步回归 Batch 184 的 8 例安全测试。

## 弃选方案

### 方案 A: 立即引入 nsjail（容器内叠加 OS 级沙箱）

- 优点：syscall 级强隔离，理论逃逸面最小。
- 缺点：nsjail 需 root/能力位运行、依赖 glibc 版本对齐；Windows 开发环境不可用；
  与 python-sdk 持久 PTY 交互调试成本高；生产 Railway 容器内再套沙箱对
  内核共享面无本质改善。
- 放弃原因：当前部署形态（L2）下收益不成比例，且显著增加运维与调试复杂度。

### 方案 B: 手写 seccomp-bpf 过滤器（平台自维护）

- 优点：无第三方依赖，过滤面可精确控制。
- 缺点：过滤器维护即安全责任（syscall 面随运行时/Node/PTY 演进漂移）；
  误杀合法 syscall 导致任务静默失败难排查。
- 放弃原因：高维护成本与误伤风险，交给成熟沙箱（bubblewrap/nsjail）更稳妥。

### 方案 C: 双容器部署（平台容器与 DSH 执行容器分离）

- 优点：L2 隔离粒度更细，DSH 崩溃不影响平台主服务。
- 缺点：跨容器任务文件/结果传输协议需新设计；Railway 同服务多容器
  编排成本上升；当前 DSH 任务频率低（并发闸门默认 2），收益有限。
- 放弃原因：作为未来可选项保留；当前形态不引入（避免为低频任务增加
  架构复杂度）。

## 关联

- 实现：Batch 184 `app/services/dsh/dsh_runner.py`（L1 加固）、
  `app/core/config.py`（DSH_MAX_CONCURRENT / DSH_MAX_TASK_CHARS）
- 相关 ADR：ADR-0018（DSH 集成与 C172-1 沙箱条件）、ADR-0015（运维发布控制面）
- C 条件：C184-1（本 ADR 关闭）；触发条件触发时登记新 C 条件
