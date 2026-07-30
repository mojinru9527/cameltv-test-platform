---
title: "Batch 57 Linux lockfile license-audit evidence"
owner: "qa-team"
created: "2026-07-30"
last_reviewed: "2026-07-30"
status: "reproducible"
expires: "2027-01-30"
tags: ["batch-57", "license", "linux", "lockfile"]
related:
  - "../../batch-57-license-audit.md"
---

# Batch 57 Linux lockfile license-audit evidence

This directory contains no credentials or proprietary test data.  It records
the exact Linux evidence for `test-platform-v2/backend/requirements.lock`.

## Reproduction record

- Source commit: `cf2c0018dbe99b59468ca4d3b20f789e5721e1c7`
- Lock SHA-256: `c52df71d6a82a12b1b0e8c5d90dd6fb99cc529e6001253516613cd68ccfefcd3`
- Linux image: `python:3.12-slim`, image digest
  `sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de`
- Runtime: Linux, Python 3.12.13, `pip-licenses` 5.5.0
- Result: 111/111 lockfile packages installed at the locked versions;
  machine-readable scan generated; exit code `0`.

The primary command was:

```sh
python -m pip install --require-hashes -r /workspace/test-platform-v2/backend/requirements.lock
python -m pip install pip-licenses==5.5.0
python -m piplicenses --format=json
```

The first container download retried after a Docker-network interruption on
the 47 MB Playwright wheel.  The recovered wheel was downloaded from its
official PyPI URL, SHA-256-checked against the lock (`54f3b39f…fd2024e`),
installed offline, and the final command above completed with
`--require-hashes` enabled.  This did not bypass the lockfile constraint.

## Artifacts

| Artifact | SHA-256 | Purpose |
| --- | --- | --- |
| `backend-requirements-lock-linux-licenses.json` | `910c9760128030c849d87d0d23c903fc26774ae12b7afe066c4a84cf71b7edc1` | 111 exact package name/version/license records and scanner flags |
| `psycopg2-binary-2.9.12-LICENSE` | `9614b85dfc9a72c5b2ca33144c1d7e1ed3b1c297459d9fb28a6a5762c2e8d71b` | Exact copy of the installed distribution's license statement |

The installed source file was
`/usr/local/lib/python3.12/site-packages/psycopg2_binary-2.9.12.dist-info/licenses/LICENSE`;
and SHA-256 is
`9614b85dfc9a72c5b2ca33144c1d7e1ed3b1c297459d9fb28a6a5762c2e8d71b`.

`fastembed==0.8.0` and `py-rust-stemmers==0.1.8` remain scanner metadata
flags in the JSON.  Their exact release-package LICENSE files were previously
reviewed as Apache-2.0 and MIT respectively; the report records this as a
metadata correction rather than silently suppressing the scanner output.
