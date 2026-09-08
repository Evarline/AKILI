/**
 * Presenting a Binance Spot symbol.
 *
 * The backend sends one string, e.g. "BTCUSDT" — it does not send a base asset,
 * a quote asset, or an asset's full name. To show "BTC / USDT" the pair has to
 * be split, so the split is done conservatively: only against a fixed list of
 * quote assets, and the raw symbol is returned unchanged when none matches.
 * Nothing is guessed, and no asset name ("Bitcoin") is ever attached — the
 * backend does not provide one, so the UI does not show one.
 */

/**
 * Quote assets AKILI splits on, longest first so that "BTCUSDT" resolves to
 * BTC/USDT rather than BTC/USD + T. These are Binance Spot quote assets, not a
 * claim about which pairs exist.
 */
const QUOTE_ASSETS = [
  'USDT',
  'FDUSD',
  'TUSD',
  'USDC',
  'BUSD',
  'TRY',
  'EUR',
  'BRL',
  'BNB',
  'BTC',
  'ETH',
  'DAI',
] as const

export type SplitSymbol = {
  /** The base asset when the symbol could be split, else null. */
  base: string | null
  /** The quote asset when the symbol could be split, else null. */
  quote: string | null
  /** Always the backend's own symbol string, unaltered. */
  raw: string
}

export function splitSymbol(symbol: string): SplitSymbol {
  for (const quote of QUOTE_ASSETS) {
    if (symbol.length > quote.length && symbol.endsWith(quote)) {
      return { base: symbol.slice(0, symbol.length - quote.length), quote, raw: symbol }
    }
  }
  return { base: null, quote: null, raw: symbol }
}

/** "BTC / USDT", or the raw symbol when it cannot be split confidently. */
export function formatPair(symbol: string): string {
  const { base, quote } = splitSymbol(symbol)
  return base && quote ? `${base} / ${quote}` : symbol
}

/**
 * The letters for an asset avatar.
 *
 * A monogram, deliberately — AKILI ships no per-asset artwork, and inventing a
 * logo mapping would put a Bitcoin mark on a symbol the backend never said was
 * Bitcoin.
 */
export function assetMonogram(symbol: string): string {
  const { base, raw } = splitSymbol(symbol)
  return (base ?? raw).slice(0, 3)
}
