/**
 * The Binance connection as a full view.
 *
 * Same real state and same real flow as the rail panel — one hook, one route —
 * with room to be explicit about server-side Binance API-key access.
 */

import type { BinanceConnectionState, ClientMetadata } from '../../api/binance'
import { BinancePanel } from '../binance/BinancePanel'
import { Icon } from '../ui/Icon'
import { Card } from '../ui/primitives'
import styles from './views.module.css'

export function BinanceView({
  state,
  metadata,
  onRefresh,
}: {
  state: BinanceConnectionState
  metadata: ClientMetadata | null
  onRefresh: () => void
}) {
  return (
    <div className={styles.view}>
      <header className={styles.viewHeader}>
        <h1 className={styles.viewTitle}>Binance account</h1>
        <p className={styles.viewLead}>
          Verify the configured Binance Spot sub-account for safe, read-only access.
        </p>
      </header>

      <Card className={styles.connectCard}>
        <BinancePanel state={state} metadata={metadata} onRefresh={onRefresh} />
      </Card>

      <section className={styles.section} aria-labelledby="distinction-heading">
        <h2 className={styles.sectionTitle} id="distinction-heading">
          Two different things
        </h2>
        <div className={styles.distinction}>
          <div className={styles.distinctionItem}>
            <p className={styles.distinctionTitle}>
              <Icon name="user" size={15} className={styles.distinctionIcon} />
              Your AKILI account
            </p>
            <p className={styles.distinctionBody}>
              Who you are inside AKILI. There is no sign-up or login yet; in development the backend
              serves every request as one fixed user, which is a development convenience and not
              authentication.
            </p>
          </div>
          <div className={styles.distinctionItem}>
            <p className={styles.distinctionTitle}>
              <Icon name="link" size={15} className={styles.distinctionIcon} />
              Your Binance connection
            </p>
            <p className={styles.distinctionBody}>
              The server-side connection between AKILI and the configured Binance Spot account.
              Credentials never enter the browser, and trading remains disabled in this phase.
            </p>
          </div>
        </div>
      </section>

      <section className={styles.section} aria-labelledby="safety-heading">
        <h2 className={styles.sectionTitle} id="safety-heading">
          What AKILI will never ask for
        </h2>
        <ul className={styles.limits}>
          <li>
            <strong>Your Binance API secret in the browser.</strong> AKILI never asks the frontend
            to handle credentials.
          </li>
          <li>
            <strong>Trading permission.</strong> This phase only verifies and reads account data.
          </li>
          <li>
            <strong>Permission to trade, silently.</strong> Even once connected, an order requires
            your explicit approval in a separate step — and that step does not exist yet.
          </li>
        </ul>
      </section>
    </div>
  )
}
