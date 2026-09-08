/**
 * The Binance sub-account connection panel.
 *
 * This is wired to the flow the backend actually has, and to nothing else:
 *
 *   - Availability is read from `GET /api/v1/binance/connection`; the backend
 *     performs the signed account request.
 *
 * API credentials remain in the backend environment. The browser never sees or
 * submits them.
 *
 * The AKILI account (sign-up, login) is a separate concern and is not built
 * here.
 */

import type { BinanceConnectionState, ClientMetadata } from '../../api/binance'
import { Icon } from '../ui/Icon'
import { Button, Code, Unavailable } from '../ui/primitives'
import styles from './binance.module.css'
import binanceColoredIcon from '../../../Binance Icon - Colored - zonalogo.com.svg'

export function BinancePanel({
  state,
  metadata,
  onRefresh,
}: {
  state: BinanceConnectionState
  metadata: ClientMetadata | null
  onRefresh: () => void
}) {
  return (
    <div className={styles.panel}>
      {state === 'checking' ? <Unavailable title="Checking Binance connection…" /> : null}

      {state === 'available' ? <Available metadata={metadata} onRefresh={onRefresh} /> : null}

      {state === 'unavailable' ? (
        <Unavailable icon="info" title="Binance account is not configured">
          <p>
            Configure <Code>BINANCE_API_KEY</Code> and <Code>BINANCE_API_SECRET</Code> on the
            backend, then restart it. The frontend never receives either value.
          </p>
          <div className={styles.refreshRow}>
            <Button onClick={onRefresh}>
              <Icon name="refresh" size={14} />
              Check again
            </Button>
          </div>
        </Unavailable>
      ) : null}

      {state === 'unreachable' ? (
        <Unavailable icon="warning" title="Cannot reach the AKILI backend">
          <p>
            The Binance connection state is unknown because AKILI itself did not answer. Start the
            backend, then check again.
          </p>
          <div className={styles.refreshRow}>
            <Button onClick={onRefresh}>
              <Icon name="refresh" size={14} />
              Check again
            </Button>
          </div>
        </Unavailable>
      ) : null}
    </div>
  )
}

function Available({
  metadata,
  onRefresh,
}: {
  metadata: ClientMetadata | null
  onRefresh: () => void
}) {
  return (
    <div className={styles.available}>
      <p className={styles.lead}>
        AKILI is connected to the configured Binance Spot account. Credentials remain on the
        backend and are used only for read-only account access in this phase.
      </p>
      <button className={styles.connectButton} type="button" onClick={onRefresh}>
        <img src={binanceColoredIcon} alt="" />
        Check Binance connection
      </button>

      <div className={styles.limitation}>
        <Icon name="info" size={15} className={styles.limitationIcon} />
        <div>
          <p className={styles.limitationTitle}>Read-only account access</p>
          <p className={styles.limitationBody}>
            AKILI can read the configured Spot account and balances. Trading, withdrawals, futures,
            margin, and order access are disabled in this phase.
          </p>
        </div>
      </div>

      {metadata ? (
        <dl className={styles.metadata}>
          <div className={styles.metadataRow}>
            <dt>Client</dt>
            <dd>{metadata.client_name}</dd>
          </div>
          <div className={styles.metadataRow}>
            <dt>Client ID</dt>
            <dd className={styles.metadataMono}>{metadata.client_id}</dd>
          </div>
          <div className={styles.metadataRow}>
            <dt>Redirect</dt>
            <dd className={styles.metadataMono}>{metadata.redirect_uris.join(', ')}</dd>
          </div>
        </dl>
      ) : null}
    </div>
  )
}
