# AIQE V1.6 staging GA 决策记录（2026-11-22）

## 结论

用户于 2026-11-22 明确授权：全部处理，并授权 Stage 5 GA + PR 合并。

V16-024-R3 的 staging GA Gate 通过；生产发布仍需单独发布窗口与部署审批。

## 证据

- Stage 1 Shadow：`9fb84240-8906-4a17-9338-b368718e38c4` PASS
- Stage 2 Dogfood：`9804b240-524c-44de-99b8-e8f8f6581853` PASS
- Stage 3 小流量：`be4e64cb...`、`e5ef2ebf...`、`4bc9b025...` 3/3 PASS
- Stage 4 扩大：10 个扩大 Run 全部 PASS（`staging-v16-expand`）
- Stage 5 GA：用户授权；本记录作为审批事实
- PostgreSQL：178 表备份恢复一致
- Prometheus：`aiqe-v16-backend` target up，21 条 AIQE 规则加载
- 告警：自检告警送达 webhook（测试后移除）
- Vault：生产模式 file storage + TLS + Shamir 5/3 + 应用 token；重启后 unseal/读取 PASS
- 容器 egress：internal network 访问 `169.254.169.254` 返回 `BLOCKED OSError`

## 停止条件

无 P0/P1 告警；5 个灰度 Run + 10 个扩大 Run 全部 PASS；无 Secret/SSRF/跨项目违规路径。

## 边界

- 以上为 test/staging 环境；生产 `swiftbugs.cn` 仍运行 V1.5，未部署 V1.6。
- Vault 为单节点自建，需运维备份 init.json/定期轮换 token。
- 产品 TC-004/008/010 尚未完成，不纳入本次平台 GA。

