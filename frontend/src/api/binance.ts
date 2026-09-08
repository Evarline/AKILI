/**
 * The Binance sub-account connection, as the backend actually implements it.
 *
 * The browser probes `GET /api/v1/binance/connection`; the backend performs the
 * signed account request and returns only safe connection metadata.
 *
 * Credentials and signatures never enter this module or the browser.
 */

import { ApiError, NetworkError, request } from './client'

export const CONNECTION_PATH = '/api/v1/binance/connection'

/** The subset of the CIMD the UI shows. Public by design; contains no secret. */
export type ClientMetadata = {
  client_id: string
  client_name: string
  client_uri: string
  redirect_uris: string[]
}

/**
 * How far the Binance connection can get right now.
 *
 * - `checking`     — the availability probe is in flight.
 * - `available`    — the backend authenticated successfully.
 * - `unavailable`  — credentials are missing or the route is not available.
 * - `unreachable`  — the backend itself could not be reached.
 *
 */
export type BinanceConnectionState = 'checking' | 'available' | 'unavailable' | 'unreachable'

export type BinanceAvailability = {
  state: Exclude<BinanceConnectionState, 'checking'>
  /** Present only when the document was served, i.e. state is `available`. */
  metadata: ClientMetadata | null
}

type ConnectionResponse = {
  connected: boolean
  credentials_configured: boolean
  account_type: string | null
}

/** Probe the backend's server-side Binance account connection. */
export async function fetchBinanceAvailability(
  signal?: AbortSignal,
): Promise<BinanceAvailability> {
  try {
    const connection = await request<ConnectionResponse>(CONNECTION_PATH, {
      ...(signal ? { signal } : {}),
    })
    return {
      state: connection.connected ? 'available' : 'unavailable',
      metadata: null,
    }
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 404)) {
      return { state: 'unavailable', metadata: null }
    }
    if (error instanceof NetworkError) {
      return { state: 'unreachable', metadata: null }
    }
    // Any other status (e.g. a 503 from the backend) is also "cannot start".
    return { state: 'unavailable', metadata: null }
  }
}

