/// <reference types="vite/client" />

/**
 * Build-time configuration reaching the bundle.
 *
 * Only non-secret values belong here. `VITE_API_BASE_URL` is the AKILI backend's
 * URL; there is deliberately no Binance URL, no API key, and no token — the
 * frontend has no use for one and must never carry one.
 */
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
