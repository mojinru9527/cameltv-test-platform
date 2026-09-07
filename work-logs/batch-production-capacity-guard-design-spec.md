# Production Capacity Guard - Interface Design

No product UI changes. Python standard library only; JSON is the operator
interface. SSH transports base64-encoded Python source and JSON arguments,
not shell-interpolated file paths or secrets.

## Capacity admission

Reserve = max(8 GiB, archive_bytes * 3 + 2 GiB) before upload;
max(8 GiB, archive_bytes * 2 + 2 GiB) before import. Factors are conservative
admission policy, not a proof of compressed-image expansion size. Check the
release directory, Docker root and containerd root (when present), grouped by
filesystem to avoid misleading summed capacities. Require 5% free inodes
and at least 1024 when the filesystem reports inode accounting. Inspection
failure blocks. Check is a point-in-time snapshot, not a disk reservation.

## Cleanup

Release tag grammar: release-YYYYMMDD-NNNN. Allowlist only cameltv-tp-backend
and cameltv-tp-frontend. Require at least two explicit retained complete pairs.
Protect two latest release tags, releases younger than 48 hours, all container
image IDs and any image having a tag outside the allowlist grammar.
Only exact regular non-symlink *-backend.tar/*-frontend.tar archives older
than 48 hours are candidates; no recursion and no backup suffixes.

Preview is the default. Apply requires the exact SHA-256 digest of a freshly
computed plan. Recheck container/image references before image deletion;
never force-delete and never call system/image/volume prune. An exclusive
host file lock coordinates this tool with release-console deploy/rollback.
Operators must pause other out-of-band deployment tools during application.

## Results

JSON report: protected tags, image-tag candidates, archive candidates,
archive bytes (exact), disk free bytes, plan digest. Image reclaimed space
is deliberately not estimated by adding image virtual sizes.
Failures exit nonzero. Partial application is reported by the process failure;
rerun preview rather than replaying approval. Retention never deletes the
database, audit trail, credentials, dumps or running/stopped containers.
