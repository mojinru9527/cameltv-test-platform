/** Match only the API v1 namespace, never similarly prefixed frontend routes. */
export const API_V1_PROXY_PATTERN = '^/api/v1(?:/|$)'

/** Match the AITDE v2 namespace (V30-002); proxied to the same backend. */
export const API_V2_PROXY_PATTERN = '^/api/v2(?:/|$)'
