# Third-party distribution notices

This file records third-party notice handling for artifacts distributed from
`test-platform-v2`. It is an engineering record, not legal advice.

## psycopg2-binary 2.9.12

The backend lockfile includes `psycopg2-binary==2.9.12`. Its installed
distribution license statement is retained at
`work-logs/evidence/batch-57-license-audit/psycopg2-binary-2.9.12-LICENSE`.
It states LGPL version 3 or later and includes a special exception for linking
with OpenSSL.

For every external distribution of a backend wheel, container image, offline
bundle, or source archive that includes this dependency, the release process
must retain that license statement, the LGPLv3-or-later text, and the OpenSSL
linking exception with the distributed artifact. The release owner must assess
the concrete distribution method and any additional bundled-library notices
before release; this repository does not provide a legal conclusion.

Official upstream reference: <https://www.psycopg.org/docs/license.html>.
