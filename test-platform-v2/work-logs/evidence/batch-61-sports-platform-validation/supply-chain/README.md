# Batch 61 W2 Supply-chain Evidence Summary

## Sports UI

| Check | Result |
| --- | --- |
| Dependency change | `@midscene/web 0.20.1 -> 1.10.8` |
| Exact overrides | `js-yaml 4.3.0`, `sharp 0.35.0`, `uuid 11.1.1` |
| Clean install | PASS, 284 packages |
| Production audit | PASS, 0 vulnerabilities |
| Compatibility | typecheck PASS; security `17/17`; Playwright collection `38 tests in 9 files` |

This closes the sports UI dependency portion of B60-P1-023. No credentials, Test5 traffic or generated browser evidence were involved.

## Backend observation

| Field | Value |
| --- | --- |
| Tool | isolated `pip-audit 2.10.1`; not yet repository-locked/approved |
| Input | `test-platform-v2/backend/requirements.lock` |
| Dependencies audited | 118 |
| Result | exit 1; 1 known vulnerability |
| Package | `ecdsa 0.19.2` via `python-jose` |
| Advisory | `PYSEC-2026-1325` / `GHSA-wj6h-64fc-37mp` / `CVE-2024-23342` |
| Severity | high, CVSS 7.4 |
| Patched version | none published |
| Current usage context | application JWT algorithm defaults to HS256; affected ECDSA signing/key-generation/ECDH path is not configured |
| Disposition | B61-P1-001 FAIL; no named/expiring risk acceptance |

The raw JSON report was stored in a system temporary directory outside the repository and is intentionally not committed. This summary contains no credentials, private data or raw service response.
