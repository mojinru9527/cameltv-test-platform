# release-20260913-0001 Production Verification

Date: 2026-09-13 Asia/Shanghai  
Environment: production Tencent Lighthouse `111.230.155.116`  
Release: `release-20260913-0001`  
Deployment: `0da8120c92fc46c592f54ccbf78cc9f2`  
State: `PRODUCTION_VERIFIED`

## 1. Runner availability

The self-hosted Runner `win-internal-001` was manually recovered and then switched to the user-level scheduled task `CamelTvActionsRunner`.

- Trigger: current-user logon.
- Guard process: `F:\CamelTv-actions-runner\run-loop.cmd`.
- Failure behavior: `run.cmd` is restarted after exit; Task Scheduler also has `RestartCount=999`, `RestartInterval=PT1M`.
- Execution time limit: unlimited.
- Battery stop policy: disabled.
- Real restart drill: killed the Listener while idle; the loop started a new Listener, recovered from the temporary GitHub session conflict, and returned to `online`.

## 2. Production capacity

Read-only cleanup preview digest:
`2831f18e86667a8fad838bda04fe103758541402ebb1dd926c9938cdc3a18c59`

Verified off-production archives:

| Archive | Bytes | SHA-256 |
|---|---:|---|
| release-20260903-0001-backend.tar | 1398110208 | 076e34fba0399b78dac8f1cda799d4bd526108500cefd1aa7c28b9f00526f045 |
| release-20260903-0001-frontend.tar | 27321856 | e7672d5c08089048c36294a51217d347d649e639dbf36cc5b2b980cb00b6f966 |
| release-20260905-0001-backend.tar | 1398996992 | 7ec3ddc8c92d41491c4f875de233c90178e8b8d8d6639c5553e3fb39d8b05d5b |
| release-20260905-0001-frontend.tar | 27319296 | 82df129419d902741137c92b35413c60704cf09feff9a9ac792df2eef3461e4b |

Protected cleanup removed the four verified historical archives and four corresponding release tags. The free space increased from approximately 2.4 GiB to 5.1 GiB. A separately reviewed redundant alias pair (`prev-prod-20260905` with `release-20260903-0001`, no container references and covered by verified archives) was then removed, increasing free space to approximately 9.5 GiB. Main, release-20260906-0001, release-20260907-0001 and all container references remained protected.

The first publish attempt stopped before import because the import gate observed 8,363,343,872 bytes free, below 8 GiB. Journald retention was reduced to 50 MiB (freed 258.2 MiB), then a new deployment record was created from the unchanged manifest and published successfully.

## 3. Backup

PostgreSQL custom-format backup created through the release console:

- Remote: `/opt/cameltv-backup/cameltv-prod-20260912-175322.dump`
- Local copy: `F:\CamelTv-safe-backup\production-db-backups-20260913\cameltv-prod-20260912-175322.dump`
- Bytes: `59057533`
- SHA-256: `12c44de7c850ae11643e1d1369f9f8eef295a4777ef50919a5cb593f8086d8c1`
- Download verification: PASS

Release-console state/config backup:

- Remote: `/opt/cameltv-release-console/state-backup-20260913.tar.gz`
- Bytes: `16096`
- SHA-256: `f148956f57ae498f563575f5a13d7e9f7cc3c103c714f2dea64be059d183d986`

## 4. Release set

Source commit: `3f9f3d88edc6f83d8bfa9d0550cfe712215220bd`

| Component | Config digest | Archive bytes | Archive SHA-256 |
|---|---|---:|---|
| backend/API | `sha256:39d1ae64c7b78dcd7ede59ae22f5db8e85d286d325bcfad668866dbfd9147ade` | 228955136 | 1824133218363071dee03ce28af4c98335eba0930e807b2f6fdba4d52558f8ca |
| frontend | `sha256:76bc30d3874a7d03207fe7c556993a04d47090d4793ca344ca2ca904a405ec35` | 27328512 | 99898f805d276cbb7175e8cd4092c291e104d8462244c2678913ba47ba0a1725 |
| runner | `sha256:985984defd7e931293d137d58901060e403b0142ad435c85bf7e6f36843b998e` | 1397317120 | 68b4f09f60b6d0e7dd605450598a3ddf6e600c59588eec8d31ccb7c9e66993e7 |
| execution config | `sha256:7f0df2b8e67191862073b07c7d56878a2092cab599aecce18349707ca68db927` | 2619 | 7f0df2b8e67191862073b07c7d56878a2092cab599aecce18349707ca68db927 |

All four files were uploaded to production and remote SHA-256 values matched the local artifacts before validation.

Manifest SHA-256:
`08fb3626829acdbfac3fb269115ab5434d9652fef1d1c7638a498c9f17c76da9`

## 5. Production topology

The release switched production from combined backend to the split topology:

- `cameltv-tp-production-backend-1`: `cameltv-tp-backend:main`
- `cameltv-tp-production-runner-1`: `cameltv-tp-runner:main`
- `cameltv-tp-production-aitde-worker-1`: `cameltv-tp-runner:main`
- `cameltv-tp-production-frontend-1`: `cameltv-tp-frontend:main`
- `cameltv-tp-production-postgres-1`: healthy, unchanged
- `aitde-temporal`: healthy, unchanged

The runner applied migration `20260915_plan_dispatch` and joined Temporal queue `worker-test`.

## 6. Fifteen-minute observation

Observation file:
`/opt/cameltv-release/observe-release-20260913-0001.tsv`

| Metric | Result |
|---|---:|
| Samples | 89 |
| Bad health responses | 0 |
| Minimum `MemAvailable` | 1982.9 MiB |
| Maximum `MemAvailable` | 2028.1 MiB |
| Maximum health latency | 0.101124 s |
| Minimum `SwapFree` | 1714 MiB |
| Container restarts | 0 |
| OOM kills | 0 |

The production health endpoint returned `{"code":0,"msg":"ok","data":{"status":"ok","version":"2.3.0"}}` throughout the observation.

Container memory snapshot near the end:

| Container | Memory |
|---|---:|
| backend | 196.9 MiB / 384 MiB |
| runner | 242.3 MiB / 1536 MiB |
| aitde-worker | 163.5 MiB / 512 MiB |
| frontend | 5.48 MiB |
| postgres | 169.3 MiB |
| temporal | 123.1 MiB |

Release-console verification returned:

`production verified (health ok)` with all application containers healthy and `front=200`.

## 7. Follow-up fixes merged

- PR #416: accept reachable 4xx health responses and mask dynamically generated business tokens.
- PR #417: serialize Playwright API regression to one worker for the Windows self-hosted Runner.
- PR #418: target Test API regression at `https://camel-test5.elelive.cn`.
- PR #419: allow release capacity admission to accept split three-archive release sets.

## 8. Current risks

- Disk free after importing the new split image set is approximately 3.4 GiB. Further cleanup must preserve the current release, verified rollback, stopped-container references, database and evidence.
- The Runner task requires the current Windows user to log on after host reboot; it is not a machine-wide Windows service because the account is not elevated.
- Production long-lived and mixed-workload sizing remains a release prerequisite for raising concurrency; the successful short observation does not prove arbitrary multi-task capacity.
