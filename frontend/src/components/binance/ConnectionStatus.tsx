/**
 * The Binance connection state, in the header.
 *
 * The state comes from the backend's safe signed account check. No credential
 * or signature is available to the browser.
 */

import type { BinanceConnectionState } from '../../api/binance'
import { cx } from '../ui/primitives'
import styles from './binance.module.css'
import binanceWhiteIcon from '../../../Binance Icon - White - zonalogo.com.svg'

const LABELS: Record<BinanceConnectionState, { text: string; tone: string }> = {
  checking: { text: 'Checking…', tone: 'idle' },
  available: { text: 'Connected', tone: 'ok' },
  unavailable: { text: 'Not configured', tone: 'idle' },
  unreachable: { text: 'Backend offline', tone: 'down' },
}

export function ConnectionStatus({
  state,
  onSelect,
}: {
  state: BinanceConnectionState
  onSelect: () => void
}) {
  const label = LABELS[state]

  return (
    <button type="button" className={styles.headerStatus} onClick={onSelect}>
      <span className={styles.headerIcon} aria-hidden>
        <img src={binanceWhiteIcon} alt="" />
      </span>
      <span className={styles.headerText}>
        <span className={styles.headerTitle}>Binance</span>
        <span className={styles.headerState}>
          <span
            className={cx(
              styles.dot,
              label.tone === 'ok' && styles.dotOk,
              label.tone === 'warn' && styles.dotWarn,
              label.tone === 'down' && styles.dotDown,
            )}
            aria-hidden
          />
          {label.text}
        </span>
      </span>
    </button>
  )
}
