# Batch 247 — RapidOCR production evidence

> Date: 2026-09-17 | PR: #457 | Git SHA:
> `ddd5650f67c7098436952f106f5a48ac021e56f2`

## Deployment

- Release: `release-20260917-0001`
- Deployment id: `5cee822bd24e4961a1b3b2f674e73ee1`
- State: `PRODUCTION_VERIFIED`
- Runtime: split topology (`api` + `runner` + `ai-gateway` + frontend)
- Backup before deployment:
  `/opt/cameltv-backup/cameltv-prod-20260916-173516.dump` (65 MiB)

The API and runner images were rebuilt from the merged commit. The verified
previous frontend and AI Gateway images were retagged into this release because
their source did not change. The runner build reused the verified runner image
and installed only the five newly locked OCR packages from
`requirements.runner.lock`; the API patch copied the same merged application
source without adding OCR-only runtime dependencies.

## Artifact identity

| Part | Release image | Config digest |
|---|---|---|
| backend | `cameltv-tp-backend:release-20260917-0001` | `sha256:ed01f2789b440dd50d21dbbf255caa2801337f67dd2845f4905dfde0512c1085` |
| runner | `cameltv-tp-runner:release-20260917-0001` | `sha256:ecbc42647626a653d09725e0edf50b27a03887c3c43b2050c2cff608b345466c` |
| frontend | `cameltv-tp-frontend:release-20260917-0001` | `sha256:1eefb8853a39f5c4eacaab76615e065171b5cc1b590361b162bcf4bfa51ce532` |
| ai-gateway | `cameltv-tp-ai-gateway:release-20260917-0001` | `sha256:3ab7ab754376a6f5a75129e20649f4824021f7443da2566811ea88ac40b3dc78` |

Execution configuration SHA-256:
`7a612e43a5a8764d18b6411d1b9a74f7448a6a8eb5a4fa123f9485ac2151c77d`.
Remote artifact verification and capacity admission passed before deployment.

## Production verification

- Release console verify returned `PRODUCTION_VERIFIED`; external
  `/api/v1/open/health` and `/` both returned HTTP 200.
- All six production services were healthy: frontend, backend, runner,
  aitde-worker, ai-gateway and PostgreSQL.
- `sportsadmin` login returned `user_id=4`.
- Running container image IDs matched the new `:main` image IDs for backend,
  runner, frontend and AI Gateway.
- Runner settings resolved to `lanhu_capture_device_scale_factor=2.0` and the
  default built-in RapidOCR command.
- No `Traceback`, `ModuleNotFound`, `error`, `critical` or `failed` lines were
  found in the backend, runner or aitde-worker logs after deployment.

### Real OCR smoke

Smoke image:
`F:\CamelTv-safe-backup\rapidocr-smoke.png` (`SHA256
FBF7C4178D1A240795EDD0E0E1486427B4BDAF9735EA6F9C13F989B68A365602`).

Production runner output:

```json
{"text": "赛事回放详情页面", "confidence": 0.9995916187763214, "bbox": [27, 39, 449, 98]}
{"text": "matchld 必填 分钟数必填", "confidence": 0.9639427736401558, "bbox": [27, 119, 647, 177]}
```

## Legacy fail-closed regression

The Legacy mutation paths remain read-only after the Batch 247 deployment:

| Route | Result |
|---|---|
| `POST /api/v1/apitest/tasks/1/cancel` | 410 |
| `POST /api/v1/apitest/tasks/1/retry-failed` | 410 |
| `DELETE /api/v1/apitest/tasks/1` | 410 |
| `POST /api/v1/apitest/runner/claim` | 410 |

The canonical execution path remains the only writable execution path.

## Rollback anchor

The four `release-20260916-0003` images remain installed and are available to
the release console rollback path. The older release tarballs were removed only
after the new release reached `PRODUCTION_VERIFIED`, to satisfy the documented
capacity admission gate. Database backup and image anchors remain intact.
