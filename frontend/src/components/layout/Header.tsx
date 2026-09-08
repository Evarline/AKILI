/**
 * The header: the AKILI mark and wordmark, the Binance connection state, and
 * the sidebar toggle on small screens.
 *
 * The reference shows an account chip with a user's name and initial. AKILI's
 * backend does not send one — `CurrentUser` is an opaque id and is never
 * returned to the client — so there is no name to show and none is invented.
 * What replaces it is the backend's real reachability, which the frontend can
 * actually determine.
 */

import type { BinanceConnectionState } from '../../api/binance'
import type { BackendHealth } from '../../hooks/useBackendHealth'
import { AkiliMark } from '../brand/AkiliMark'
import { ConnectionStatus } from '../binance/ConnectionStatus'
import { Icon } from '../ui/Icon'
import { cx } from '../ui/primitives'
import styles from './layout.module.css'

export function Header({
  binanceState,
  health,
  onSelectBinance,
  onToggleSidebar,
  isSidebarOpen,
}: {
  binanceState: BinanceConnectionState
  health: BackendHealth
  onSelectBinance: () => void
  onToggleSidebar: () => void
  isSidebarOpen: boolean
}) {
  return (
    <header className={styles.header}>
      <button
        type="button"
        className={styles.sidebarToggle}
        onClick={onToggleSidebar}
        aria-expanded={isSidebarOpen}
        aria-controls="akili-sidebar"
        aria-label={isSidebarOpen ? 'Hide conversations' : 'Show conversations'}
      >
        <Icon name="sidebar" size={18} />
      </button>

      <div className={styles.brand}>
        <AkiliMark size={30} title="AKILI" />
        <span className={styles.brandText}>
          <span className={styles.wordmark}>AKILI</span>
          <span className={styles.tagline}>Your Binance AI Agent</span>
        </span>
      </div>

      <div className={styles.headerRight}>
        {health.status === 'down' ? (
          <p className={styles.offline} role="status">
            <span className={cx(styles.offlineDot)} aria-hidden />
            AKILI backend offline
          </p>
        ) : null}
        <ConnectionStatus state={binanceState} onSelect={onSelectBinance} />
      </div>
    </header>
  )
}
