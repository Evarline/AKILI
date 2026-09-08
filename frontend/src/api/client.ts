/**
 * The single HTTP seam between AKILI's frontend and AKILI's backend.
 *
 * Architecture this file enforces:
 *
 *     Frontend -> AKILI backend -> agent -> capability layer
 *              -> MarketDataProvider -> BinanceRESTProvider -> Binance
 *
 * The browser therefore talks to one origin: AKILI's own. There is no Binance
 * base URL here, no API key, and no signing — the frontend holds no credential
 * of any kind, and every market figure it shows arrived through the backend.
 *
 * In development, requests go to same-origin paths and Vite proxies them to the
 * backend (see vite.config.ts), so no CORS configuration is needed on the
 * backend. `VITE_API_BASE_URL` can point at a deployed backend instead; it is a
 * URL, never a secret.
 */

const rawBase: string = import.meta.env['VITE_API_BASE_URL'] ?? ''
/** Trailing slash removed so path joining is unambiguous. */
export const API_BASE_URL = rawBase.replace(/\/+$/, '')

/** Backend failures the UI can react to, with the backend's own `detail` text. */
export class ApiError extends Error {
  readonly status: number
  readonly detail: string | null

  constructor(status: number, detail: string | null, message?: string) {
    super(message ?? detail ?? `Request failed with status ${status}`)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

/** The request could not reach AKILI at all: offline, DNS, backend down. */
export class NetworkError extends Error {
  constructor(cause?: unknown) {
    super('Could not reach AKILI')
    this.name = 'NetworkError'
    this.cause = cause
  }
}

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`
}

/** Pull FastAPI's `{"detail": ...}` out of an error body, without trusting its shape. */
async function readDetail(response: Response): Promise<string | null> {
  try {
    const body: unknown = await response.json()
    if (body && typeof body === 'object' && 'detail' in body) {
      const detail = (body as { detail: unknown }).detail
      if (typeof detail === 'string') return detail
      // 422 from FastAPI is a list of validation errors; it is a client bug, not
      // something to render at the user, so it is summarised rather than shown.
      if (Array.isArray(detail)) return 'The request was rejected as invalid'
    }
  } catch {
    /* No JSON body, or not JSON at all. Fall through to the status alone. */
  }
  return null
}

type RequestOptions = {
  method?: 'GET' | 'POST'
  body?: unknown
  signal?: AbortSignal
}

/** Perform a JSON request against the AKILI backend. */
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, signal } = options

  let response: Response
  try {
    response = await fetch(apiUrl(path), {
      method,
      headers: {
        accept: 'application/json',
        ...(body === undefined ? {} : { 'content-type': 'application/json' }),
      },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      ...(signal ? { signal } : {}),
    })
  } catch (cause) {
    // An aborted request is the caller's own doing, not a network failure.
    if (cause instanceof DOMException && cause.name === 'AbortError') throw cause
    throw new NetworkError(cause)
  }

  if (!response.ok) {
    throw new ApiError(response.status, await readDetail(response))
  }

  if (response.status === 204) return undefined as T
  try {
    return (await response.json()) as T
  } catch (cause) {
    throw new ApiError(response.status, null, 'AKILI returned a response that could not be read')
  }
}
