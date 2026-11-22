# Vault Transit 外部 KMS 部署与验证

> 2026-11-21；测试机 `aiqe-test-net`；开发/测试模式，不是生产持久化部署。

## 部署

- 镜像：`hashicorp/vault:1.18`
- 容器：`aiqe-vault`
- 地址：`http://127.0.0.1:8200`（宿主）/ `http://aiqe-vault:8200`（容器网络）
- 配置：`/opt/aiqe-vault/vault.env`（chmod 600，含 dev root token）
- Transit：`transit/`，key `aiqe-secrets`，`aes256-gcm96`
- 模式：`vault server -dev`，**仅测试**；生产必须文件/Consul 存储 + 自动解封/KMS 自动解封。

## 代码

- `VaultTransitStore`：`test-platform-v2/backend/app/aiqe/security/external_secret_store.py`
- provider：`AIQE_SECRET_STORE_PROVIDER=vault`
- 配置：`AIQE_VAULT_ADDR` / `AIQE_VAULT_TOKEN` / `AIQE_VAULT_TRANSIT_MOUNT` / `AIQE_VAULT_TRANSIT_KEY`

## 验证

- Vault Transit encrypt/decrypt roundtrip：`vault-live-test` → 密文 → 明文一致；
- 本地索引文件只含 `vault:v1:...` 密文，无明文；
- 缺地址/token/key 或 Vault HTTP 失败：`ExternalStoreUnavailable`，fail closed；
- 单测：`tests/test_aiqe_v16_003_vault_transit.py` 3 passed；
- 既有加密文件后端测试 7 passed。

## 边界 / 待办

- 当前 test backend 镜像仍为 `v14-test`，不含该 provider；需要重建当前 V1.6 镜像后才能在应用内使用；
- Vault 为 dev 模式，重启会丢数据；生产需持久化存储、TLS、自动解封、备份与轮换。
