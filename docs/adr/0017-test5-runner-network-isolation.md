---
title: "ADR-0017: Test5 验收执行器网络隔离（WSL/容器）"
owner: "devops-team"
created: "2026-08-02"
last_reviewed: "2026-08-02"
status: "accepted"
expires: "2027-02-02"
tags: ["adr", "network", "vpn", "test5", "runner", "isolation", "wsl"]
related:
  - "0015-operations-release-control-plane.md"
  - "0016-three-repository-separation.md"
  - "../../test-platform-v2/docs/operations/test5-runner-isolation.md"
---

# ADR-0017：Test5 验收执行器网络隔离（WSL/容器）

## 状态

✅ 已采纳（执行器搭建与实测在 batch-66）

## 日期

2026-08-02

## 背景

Test5 验收（`*.elelive.cn` 内网）必须通过 OpenVPN 访问；AI（DeepSeek）与生产访问依赖 vpn07
（Clash Meta TUN）全局代理。同一台 Windows 主机上两个「全局」隧道存在默认路由与 DNS 互斥：

- batch-64 实测：OpenVPN `pull-filter ignore redirect-gateway` + hosts 可本机共存，
  `curl https://api.deepseek.com` 链路验证通过（返回真实服务器 401）；
- 但本机共存依赖 Windows 路由表、DNS 顺序与接口 metric 的手工维护，脆弱且难以自动化；
- 仓库旧《双 VPN 切换手册》的「来回切换」模式已暂停（2026-07-29），需要可长期维护的替代方案。

## 决策

采用**执行器网络隔离**：Test5 验收在独立网络栈（WSL2 / Docker 容器 / 独立 VM）内执行，
Windows 主机保持 vpn07 全局，只承担 AI 与测试平台。执行器即 ADR-0015 的「环境执行器（Test5 域）」，
与主机仅交互共享目录、产物与控制面指令，不共享网络隧道。

### 形态优先级

1. WSL2（首选，已具备）：Linux 工具链 + 零额外成本；batch-66 验证 `/dev/net/tun`；
   Windows 11 优先尝试 mirrored 网络模式；
2. Docker Desktop（WSL2 后端）：环境可复现、可打包执行器镜像；
3. 独立 Hyper-V VM：兜底，网络栈完全独立。

### 关键约束

1. 主机 vpn07 全局常开，AI 可用性不受 Test5 验收影响；
2. OpenVPN 真实 CA/凭据不入库，只存模板片段；
3. 执行器产物（报告/日志）回传，不伪造验收证据（对齐 C63-2）；
4. 验证矩阵 V1–V5 全部通过才视为方案成立（batch-66 实测）。

## 后果

### 正面影响

- ✅ AI 与 Test5 验收彻底解耦，互不干扰；
- ✅ 取代「双 VPN 切换」手工模式，可自动化、可重复；
- ✅ 与 ADR-0015 环境执行器契约一致，未来由运维发布控制面调度；
- ✅ 本机 hosts/路由表不再需要手工维护。

### 负面影响 / 权衡

- ⚠️ WSL2 tun 支持、Clash TUN 与 WSL2 NAT 交互需 batch-66 实测确认；
- ⚠️ 执行器环境本身需要维护（发行版/镜像更新、OpenVPN 配置同步）；
- ⚠️ Test5 产物回传链路需设计（共享目录/控制面 API）。

## 弃选方案

### 方案 A：本机路由分流（batch-64 实测）

- 优点：零额外环境，立即可用。
- 缺点：依赖 Windows 路由表/DNS 顺序/hosts 手工维护，脆弱且不可自动化。
- 结论：作为临时回退，不作为长期方案。

### 方案 B：双机（一台 vpn07、一台 OpenVPN）

- 优点：物理隔离最彻底。
- 缺点：需要第二台常驻机器，资源与成本高。
- 结论：过度；WSL/VM 已足够。

### 方案 C：继续双 VPN 来回切换（旧手册）

- 优点：无新环境。
- 缺点：验收窗口期 AI 不可用、手工切换易错、已暂停。
- 结论：废弃。

## 关联

- ADR-0015（环境执行器与发布控制面）
- ADR-0016（三仓边界）
- [Test5 执行器隔离方案](../../test-platform-v2/docs/operations/test5-runner-isolation.md)
