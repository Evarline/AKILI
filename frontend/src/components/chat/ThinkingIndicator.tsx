/**
 * The loading state for a turn in flight.
 *
 * Nothing but the indicator: no skeleton price, no placeholder card, no
 * greyed-out figure that could be mistaken for data arriving. It is announced
 * politely so a screen-reader user knows AKILI is working.
 */

import { AkiliMark } from '../brand/AkiliMark'
import styles from './chat.module.css'

export function ThinkingIndicator() {
  return (
    <div className={styles.thinkingRow} role="status" aria-live="polite">
      <span className={styles.agentAvatar}>
        <AkiliMark size={20} />
      </span>
      <p className={styles.thinking}>
        <span>AKILI is thinking</span>
        <span className={styles.dots} aria-hidden>
          <span />
          <span />
          <span />
        </span>
      </p>
    </div>
  )
}
