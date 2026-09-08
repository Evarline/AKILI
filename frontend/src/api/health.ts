/**
 * `GET /health` — is the AKILI backend process up?
 *
 * Used only to tell "AKILI is not running" apart from "AKILI answered with an
 * error", so the UI's failure copy can be accurate. It touches nothing external
 * on the backend side, so it stays cheap.
 */

import { NetworkError, request } from './client'

export const HEALTH_PATH = '/health'

export type Health = {
  status: string
  version: string
}

export type BackendReachability =
  | { reachable: true; version: string }
  | { reachable: false; version: null }

export async function fetchHealth(signal?: AbortSignal): Promise<BackendReachability> {
  try {
    const health = await request<Health>(HEALTH_PATH, { ...(signal ? { signal } : {}) })
    return { reachable: true, version: health.version }
  } catch (error) {
    if (error instanceof NetworkError) return { reachable: false, version: null }
    // The process answered, even if unhappily: it is reachable.
    return { reachable: true, version: '' }
  }
}
