/**
 * One AKILI turn.
 *
 * The body is `interpretation.message` — the backend-validated text the model
 * produced — followed by whatever structured card the *intent* justifies:
 *
 *   - a clarifying question, when `requires_clarification` is set;
 *   - the market-data card, when `market_data` came back with the turn;
 *   - the BUY_SPOT interpretation card, when the intent is BUY_SPOT;
 *   - an honest "not connected" note for ACCOUNT_INFORMATION, because Binance
 *     account access does not exist in the backend yet;
 *   - an honest "not supported" note for UNSUPPORTED_ACTION.
 *
 * The intent drives which card appears, and each card renders only its own
 * response fields. Nothing is displayed that the response did not contain.
 */

import type { AgentTurn } from '../../hooks/useChat'
import { MarketDataCard } from '../market/MarketDataCard'
import { BuySpotCard } from '../plan/BuySpotCard'
import { AkiliMark } from '../brand/AkiliMark'
import { Icon } from '../ui/Icon'
import { formatClock } from '../../lib/time'
import styles from './chat.module.css'

export function AgentMessage({ turn }: { turn: AgentTurn }) {
  const { interpretation, marketData } = turn

  return (
    <article className={styles.agentRow} aria-label="AKILI's reply">
      <span className={styles.agentAvatar}>
        <AkiliMark size={20} />
      </span>

      <div className={styles.agentBody}>
        <div className={styles.agentCard}>
          <p className={styles.agentText}>{interpretation.message}</p>

          {interpretation.question ? (
            <p className={styles.question}>
              <Icon name="info" size={15} className={styles.questionIcon} />
              <span>{interpretation.question}</span>
            </p>
          ) : null}

          {marketData ? <MarketDataCard facts={marketData} /> : null}

          {interpretation.intent === 'BUY_SPOT' && interpretation.parameters ? (
            <BuySpotCard
              parameters={interpretation.parameters}
              requiresClarification={interpretation.requires_clarification}
            />
          ) : null}

          {interpretation.intent === 'ACCOUNT_INFORMATION' ? (
            <IntentNote
              title="Your Binance account is not connected"
              body="AKILI cannot read balances, holdings, or order history: the Binance account connection is not finished in this build. Nothing about your account is shown, because nothing about it is known."
            />
          ) : null}

          {interpretation.intent === 'UNSUPPORTED_ACTION' ? (
            <IntentNote
              title="Not something AKILI can do"
              body="AKILI is limited to explaining, reading public market data, and interpreting a Spot purchase. Selling, withdrawing, transferring, futures, margin, and leverage are all outside what it will act on."
            />
          ) : null}
        </div>

        <p className={styles.timestamp}>
          <time dateTime={new Date(turn.receivedAt).toISOString()}>
            {formatClock(turn.receivedAt)}
          </time>
        </p>
      </div>
    </article>
  )
}

function IntentNote({ title, body }: { title: string; body: string }) {
  return (
    <div className={styles.intentNote}>
      <Icon name="info" size={15} className={styles.questionIcon} />
      <div>
        <p className={styles.intentNoteTitle}>{title}</p>
        <p className={styles.intentNoteBody}>{body}</p>
      </div>
    </div>
  )
}
