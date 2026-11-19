# 方式 2：网络实验室 / 云安全组落地映射

本文件把固定的 `policy.json` 映射到常见网络层的出站规则；`runner-egress.md` 第 5 节是 WSL2
网络实验室的实测证据（Run `55fd90cd-beb5-43f7-bf6e-d4b8cc5a17e3`）。

## 通用语义

- 默认：**拒绝所有出站**；
- 允许：`192.168.50.170:443/tcp`（Camel Test5）、`10.255.255.254:53/udp,tcp`（DNS）、loopback；
- 拒绝示例必须实测：`example.com:443`、`1.1.1.1:80` 超时；
- 每次变更记录：策略版本、审批人、导出文件 hash、Runner 身份、探测时间。

## AWS Security Group（出站）

```text
Type: Custom TCP   Protocol: TCP   Port: 443   Destination: 192.168.50.170/32
Type: DNS (UDP)    Protocol: UDP   Port: 53    Destination: 10.255.255.254/32
Type: DNS (TCP)    Protocol: TCP   Port: 53    Destination: 10.255.255.254/32
# 其余出站：不添加规则（默认拒绝）
```

导出：`aws ec2 describe-security-groups --group-ids <sg-id> > sg-egress.json`

## 阿里云 / 腾讯云安全组

- 阿里云：出方向规则，授权对象 `192.168.50.170/32`，协议 TCP，端口 443；DNS 同理；默认拒绝未匹配。
- 腾讯云：出站规则同上；导出安全组 JSON/截图并记录安全组 ID。
- 私有网络 NACL：需同时放行返回流量（有状态安全组通常不需要；NACL 需双向）。

## Linux Runner（iptables/nftables，已在 WSL2 验证）

```text
iptables -P OUTPUT DROP
iptables -A OUTPUT -o lo -j ACCEPT
iptables -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT
iptables -A OUTPUT -d 192.168.50.170 -p tcp --dport 443 -j ACCEPT
```

导出：`iptables-save > iptables-allowlist.txt`（证据目录已有该文件与 hash）。

## 生产交付物

1. `policy.json`（本目录）+ 审批人签字；
2. 安全组/NACL 导出 JSON（或 iptables-save）；
3. 从 Runner 执行的两条探测输出；
4. Runner 身份（hostname / 内网 IP / node_id）；
5. 对应 AIQE Run/Artifact（网络实验室证据已关联 Run `55fd90cd-...`）。
