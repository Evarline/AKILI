/**
 * The right-hand context rail.
 *
 * The reference fills this column with a market overview (top coins, gainers,
 * losers) and a portfolio total. Neither is reproducible: the backend has no
 * market-overview route — the only market data it produces is the single
 * reading attached to a chat turn — and no account access at all, so there is
 * no balance to total.
 *
 * So the rail shows three things that are true:
 *
 *   1. The latest reading this session actually received, if any.
 *   2. The real Binance connection state.
 *   3. Where AKILI's agent loop currently stops, marked stage by stage.
 *
 * and states plainly, where the reference had figures, that AKILI cannot
 * provide them yet.
 */

import type { BinanceConnectionState, ClientMetadata } from '../../api/binance'
import type { MarketDataFacts } from '../../types/contract'
import { formatObservedAge } from '../../lib/time'
import { decimalSign, formatPercent, formatPrice } from '../../lib/decimal'
import { formatPair } from '../../lib/symbol'
import { BinancePanel } from '../binance/BinancePanel'
import { Icon } from '../ui/Icon'
import { Code, RailCard, Unavailable, cx } from '../ui/primitives'
import styles from './layout.module.css'

/**
 * The agent loop from docs/architecture.md, with the stages this build actually
 * reaches. `done: false` is not a teaser — it is why the UI refuses to show a
 * plan, an approval, or an execution.
 */
const LOOP: Array<{ stage: string; detail: string; built: boolean }> = [
  { stage: 'Understand', detail: 'Classify what you asked for', built: true },
  { stage: 'Research', detail: 'Read public market data from Binance', built: true },
  { stage: 'Explain', detail: 'Answer from that data, not from memory', built: true },
  { stage: 'Plan', detail: 'Price and size a purchase', built: false },
  { stage: 'Validate', detail: 'Backend safety checks', built: false },
  { stage: 'Approve', detail: 'Your explicit authorization', built: false },
  { stage: 'Execute', detail: 'Binance places the order', built: false },
  { stage: 'Verify', detail: 'Confirm what Binance did', built: false },
]

export function ContextRail({
  latestReading,
  binanceState,
  binanceMetadata,
  onRefreshBinance,
}: {
  latestReading: MarketDataFacts | null
  binanceState: BinanceConnectionState
  binanceMetadata: ClientMetadata | null
  onRefreshBinance: () => void
}) {
  return (
    <aside className={styles.rail} aria-label="Context">
      <RailCard title="Latest reading">
        {latestReading ? (
          <LatestReading facts={latestReading} />
        ) : (
          <Unavailable icon="market" title="No market data read yet">
            <p>
              Ask AKILI about a price or a recent trend. It will read the data from Binance and the
              reading will appear here.
            </p>
          </Unavailable>
        )}
      </RailCard>

      <RailCard title="Binance">
        <BinancePanel
          state={binanceState}
          metadata={binanceMetadata}
          onRefresh={onRefreshBinance}
        />
      </RailCard>

      <RailCard title="Portfolio">
        <Unavailable icon="info" title="Not available yet">
          <p>
            AKILI has no access to your Binance account, so it has no balances or holdings to show.
            The connection step that would grant read access — the OAuth callback and token
            exchange — is not built yet.
          </p>
        </Unavailable>
      </RailCard>

      <RailCard title="How AKILI works">
        <ol className={styles.loop}>
          {LOOP.map((step, index) => (
            <li key={step.stage} className={cx(styles.loopStep, !step.built && styles.loopStepTodo)}>
              <span className={cx(styles.loopIndex, step.built && styles.loopIndexDone)} aria-hidden>
                {step.built ? <Icon name="check" size={12} strokeWidth={2.4} /> : index + 1}
              </span>
              <span className={styles.loopText}>
                <span className={styles.loopStage}>
                  {step.stage}
                  {!step.built ? <span className={styles.loopBadge}>not built</span> : null}
                </span>
                <span className={styles.loopDetail}>{step.detail}</span>
              </span>
            </li>
          ))}
        </ol>
        <p className={styles.loopFooter}>
          AKILI stops after Explain. Nothing in this build can place an order.
        </p>
      </RailCard>
    </aside>
  )
}

function LatestReading({ facts }: { facts: MarketDataFacts }) {
  const { ticker, symbol, capability, interval, klines, observed_at } = facts
  const sign = ticker ? decimalSign(ticker.price_change_percent_24h) : 0

  return (
    <div className={styles.reading}>
      <div className={styles.readingHead}>
        <span className={styles.readingPair}>{formatPair(symbol)}</span>
        {ticker ? (
          <span
            className={cx(
              styles.readingChange,
              'tabular',
              sign > 0 && styles.readingChangeUp,
              sign < 0 && styles.readingChangeDown,
            )}
          >
            {formatPercent(ticker.price_change_percent_24h)}
          </span>
        ) : null}
      </div>

      {ticker ? (
        <p className={cx(styles.readingPrice, 'tabular')}>{formatPrice(ticker.price)}</p>
      ) : (
        <p className={styles.readingNoPrice}>
          {klines.length} {interval} candle{klines.length === 1 ? '' : 's'} — no price in this
          reading
        </p>
      )}

      <p className={styles.readingMeta}>
        <Code>{capability}</Code>
        <span>Observed {formatObservedAge(observed_at)}</span>
      </p>

      <p className={styles.readingNote}>
        A reading taken at one instant, not a live feed. AKILI has no market overview, gainers, or
        losers list — it reads one pair at a time, when you ask.
      </p>
    </div>
  )
}
