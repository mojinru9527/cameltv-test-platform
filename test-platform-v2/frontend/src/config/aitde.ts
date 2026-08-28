/**
 * AITDE V3 feature flags (V30-001).
 * Frontend mirrors the backend `AITDE_V3_ENABLED`. When disabled the Mission
 * routes/menu are hidden (a direct navigation renders an "unavailable" state).
 */
export const AITDE_V3_ENABLED = import.meta.env.VITE_AITDE_V3_ENABLED === 'true'
