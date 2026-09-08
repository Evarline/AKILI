/**
 * The market-data card: `MarketDataFacts`, rendered.
 *
 * Every figure on this card is a field of `market_data` from the chat response —
 * a BINANCE FACT the backend read through the capability layer. The two
 * capabilities produce different cards, because they return different fields:
 *
 *   get_ticker -> `ticker`: price, 24h change (absolute and percent), 24h high,
 *                 24h low, 24h volume. These exist in
 *                 `app.binance.schemas.Ticker`, so the reference's 24h row is
 *                 real data, not decoration.
 *   get_klines -> `klines`: the candles, plus the interval they were read at.
 *                 There is no ticker in this response, so no price line is
 *                 shown — the card does not borrow a figure it was not given.
 *
 * `observed_at` is always shown: market data is a reading at an instant, and
 * presenting it as a live feed would be a lie. The asset's full name, its logo,
 * and market cap are absent because the backend does not send them.
 */

import { formatCompact, formatPercent, formatPrice, formatSignedPrice, decimalSign } from '../../lib/decimal'
import { assetMonogram, formatPair } from '../../lib/symbol'
import { formatAbsolute, formatObservedAge } from '../../lib/time'
import type { MarketDataFacts } from '../../types/contract'
import { ProvenanceLabel, cx } from '../ui/primitives'
import { CandleChart } from './CandleChart'
import styles from './market.module.css'

export function MarketDataCard({ facts }: { facts: MarketDataFacts }) {
  const { ticker, klines, symbol, interval, capability, observed_at, provenance } = facts

  return (
    <section className={styles.card} aria-label={`Market data for ${symbol}`}>
      <header className={styles.identity}>
        <span className={styles.avatar} aria-hidden>
          {assetMonogram(symbol)}
        </span>
        <div className={styles.identityText}>
          <p className={styles.pair}>{formatPair(symbol)}</p>
          {/* The backend's own symbol string, unaltered, beside the split pair. */}
          <p className={styles.symbol}>{symbol}</p>
        </div>
        {klines.length > 0 ? <CandleChart klines={klines} /> : null}
      </header>

      {ticker ? <TickerBody ticker={ticker} /> : null}

      {capability === 'get_klines' ? (
        <div className={styles.klinesMeta}>
          <span>
            {klines.length} {interval ?? ''} candle{klines.length === 1 ? '' : 's'}
          </span>
          <span className={styles.klinesNote}>
            This reading returned candles only — no current price was fetched.
          </span>
        </div>
      ) : null}

      <footer className={styles.footer}>
        <span className={styles.observed}>
          <span className={styles.observedDot} aria-hidden />
          <span>
            Observed <time dateTime={observed_at} title={formatAbsolute(observed_at)}>{formatObservedAge(observed_at)}</time>
          </span>
        </span>
        <ProvenanceLabel>{provenance}</ProvenanceLabel>
      </footer>
    </section>
  )
}

function TickerBody({ ticker }: { ticker: NonNullable<MarketDataFacts['ticker']> }) {
  const sign = decimalSign(ticker.price_change_percent_24h)
  const direction = sign > 0 ? 'up' : sign < 0 ? 'down' : 'flat'

  return (
    <>
      <div className={styles.priceBlock}>
        <p className={cx(styles.price, 'tabular')}>{formatPrice(ticker.price)}</p>
        <p
          className={cx(
            styles.change,
            'tabular',
            direction === 'up' && styles.changeUp,
            direction === 'down' && styles.changeDown,
          )}
        >
          {/* A glyph as well as a colour, so direction survives without colour. */}
          <span aria-hidden>{direction === 'up' ? '▲' : direction === 'down' ? '▼' : '■'}</span>
          <span>
            {formatPercent(ticker.price_change_percent_24h)}{' '}
            <span className={styles.changeAbsolute}>
              ({formatSignedPrice(ticker.price_change_24h)}) 24h
            </span>
          </span>
        </p>
      </div>

      <dl className={styles.stats}>
        <Stat label="24h High" value={formatPrice(ticker.high_24h)} />
        <Stat label="24h Low" value={formatPrice(ticker.low_24h)} />
        <Stat label="24h Volume" value={formatCompact(ticker.volume_24h)} />
      </dl>
    </>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.stat}>
      <dt className={styles.statLabel}>{label}</dt>
      <dd className={cx(styles.statValue, 'tabular')}>{value}</dd>
    </div>
  )
}
