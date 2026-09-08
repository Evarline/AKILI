/**
 * The AKILI backend contract, as the frontend receives it.
 *
 * These types are a direct mirror of the backend's Pydantic models — nothing is
 * added, and no field is invented here. If a field is not in this file, the
 * backend does not send it and the UI must not display it.
 *
 *   backend/app/api/chat.py            -> ChatRequest, ChatResponse
 *   backend/app/agent/schemas.py       -> Intent, Provenance, Interpretation
 *   backend/app/agent/capabilities.py  -> MarketDataFacts
 *   backend/app/binance/schemas.py     -> Ticker, Kline, Interval
 *
 * Monetary values arrive as decimal *strings*, on purpose: Binance transmits
 * them as strings so no float rounding occurs, and the backend keeps that
 * exactness end to end. They stay strings here too — the frontend formats them
 * without ever going through a float.
 */

/** `app.agent.schemas.Intent` — a closed set. */
export type Intent =
  | 'GENERAL_INFORMATION'
  | 'MARKET_INFORMATION'
  | 'ACCOUNT_INFORMATION'
  | 'BUY_SPOT'
  | 'CLARIFICATION_REQUIRED'
  | 'UNSUPPORTED_ACTION'

/** `app.agent.schemas.Provenance` — the trust class of a value. */
export type Provenance =
  | 'USER_INPUT'
  | 'MODEL_INTERPRETATION'
  | 'APPLICATION_GENERATED'
  | 'BINANCE_FACT'

/** `app.agent.schemas.Capability` — the two read-only market-data calls. */
export type Capability = 'get_ticker' | 'get_klines'

/** `app.binance.schemas.Interval` — the intervals the MVP exposes. */
export type Interval = '1h' | '4h' | '1d'

/** `app.agent.schemas.MarketDataRequest` — what the model *asked* AKILI to fetch. */
export type MarketDataRequest = {
  capability: Capability
  symbol: string
  interval: Interval | null
}

/**
 * `app.agent.schemas.BuySpotParameters` — the trade slots the model extracted
 * from the user's words. Reported as the user said them: the asset is not
 * resolved to a trading pair and the amount is not converted. Still MODEL
 * INTERPRETATION, never a fact and never a plan.
 */
export type BuySpotParameters = {
  asset: string | null
  /** Decimal string, e.g. "20" or "12.50". Never a number. */
  quote_amount: string | null
  quote_currency: string | null
}

/** `app.agent.schemas.Interpretation` — the backend-validated model output. */
export type Interpretation = {
  intent: Intent
  requires_clarification: boolean
  message: string
  question: string | null
  parameters: BuySpotParameters | null
  market_data_request: MarketDataRequest | null
  provenance: 'MODEL_INTERPRETATION'
}

/** `app.binance.schemas.Ticker` — a 24-hour rolling snapshot. All decimal strings. */
export type Ticker = {
  symbol: string
  price: string
  price_change_24h: string
  price_change_percent_24h: string
  high_24h: string
  low_24h: string
  volume_24h: string
}

/** `app.binance.schemas.Kline` — one candle. Times are ISO-8601, UTC. */
export type Kline = {
  open_time: string
  open_price: string
  high_price: string
  low_price: string
  close_price: string
  volume: string
  close_time: string
}

/**
 * `app.agent.capabilities.MarketDataFacts` — the result of one read-only call.
 *
 * A BINANCE FACT with the moment it was observed. The backend keeps it *beside*
 * the interpretation rather than inside it so the two trust classes never merge;
 * the UI keeps that separation visible.
 */
export type MarketDataFacts = {
  capability: Capability
  symbol: string
  interval: Interval | null
  /** ISO-8601 UTC instant the data was read from Binance. */
  observed_at: string
  ticker: Ticker | null
  klines: Kline[]
  provenance: 'BINANCE_FACT'
}

/** `app.api.chat.ChatRequest`. */
export type ChatRequest = {
  message: string
  conversation_id?: string
}

/** `app.api.chat.ChatResponse`. */
export type ChatResponse = {
  conversation_id: string
  agent_run_id: string
  response: Interpretation
  market_data: MarketDataFacts | null
}
