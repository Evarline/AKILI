/**
 * Response builders for tests.
 *
 * These are **test doubles for a stubbed `fetch`**, not application data: they
 * exist only inside `src/test/` and are never imported by anything under
 * `src/components`, `src/hooks`, or `src/api`. A test asserting that a real
 * price renders has to put a price somewhere; keeping every such value in this
 * one file, outside the app, is what makes "no mock data in the application"
 * checkable — see `no-mock-data.test.ts`.
 */

import type { ChatResponse, Interpretation, Kline, MarketDataFacts, Ticker } from '../types/contract'

export function interpretation(overrides: Partial<Interpretation> = {}): Interpretation {
  return {
    intent: 'GENERAL_INFORMATION',
    requires_clarification: false,
    message: 'A market order buys at whatever price is available right now.',
    question: null,
    parameters: null,
    market_data_request: null,
    provenance: 'MODEL_INTERPRETATION',
    ...overrides,
  }
}

export function ticker(overrides: Partial<Ticker> = {}): Ticker {
  return {
    symbol: 'BTCUSDT',
    price: '64188.42',
    price_change_24h: '1204.11',
    price_change_percent_24h: '1.91',
    high_24h: '64990.00',
    low_24h: '62710.53',
    volume_24h: '28412000000',
    ...overrides,
  }
}

export function kline(overrides: Partial<Kline> = {}): Kline {
  return {
    open_time: '2026-09-08T10:00:00+00:00',
    open_price: '63900.00',
    high_price: '64300.00',
    low_price: '63850.00',
    close_price: '64188.42',
    volume: '812.4',
    close_time: '2026-09-08T10:59:59+00:00',
    ...overrides,
  }
}

export function marketDataFacts(overrides: Partial<MarketDataFacts> = {}): MarketDataFacts {
  return {
    capability: 'get_ticker',
    symbol: 'BTCUSDT',
    interval: null,
    observed_at: new Date().toISOString(),
    ticker: ticker(),
    klines: [],
    provenance: 'BINANCE_FACT',
    ...overrides,
  }
}

export function chatResponse(overrides: Partial<ChatResponse> = {}): ChatResponse {
  return {
    conversation_id: '11111111-1111-4111-8111-111111111111',
    agent_run_id: '22222222-2222-4222-8222-222222222222',
    response: interpretation(),
    market_data: null,
    ...overrides,
  }
}

/** A `fetch` stub that routes by path, so tests never touch the network. */
export function stubFetch(routes: Record<string, () => Response | Promise<Response>>) {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
    for (const [path, respond] of Object.entries(routes)) {
      if (url.includes(path)) return respond()
    }
    throw new TypeError(`unstubbed request to ${url}`)
  })
}

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}
