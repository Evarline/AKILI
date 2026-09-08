/**
 * A failed turn, shown as a failure.
 *
 * The backend's error handlers never answer 200 with a substitute, and neither
 * does the UI: when a request fails, the user sees what failed and can retry the
 * exact message. No estimate, no cached figure, and no invented answer takes the
 * place of an error.
 */

import type { FailedTurn } from '../../hooks/useChat'
import { Icon } from '../ui/Icon'
import styles from './chat.module.css'

export function ErrorMessage({
  turn,
  onRetry,
}: {
  turn: FailedTurn
  onRetry: (turnId: string) => void
}) {
  return (
    <article className={styles.errorRow} role="alert">
      <span className={styles.errorAvatar} aria-hidden>
        <Icon name="warning" size={16} />
      </span>
      <div className={styles.errorCard}>
        <p className={styles.errorTitle}>{turn.title}</p>
        <p className={styles.errorDetail}>{turn.detail}</p>
        <button type="button" className={styles.retryButton} onClick={() => onRetry(turn.id)}>
          <Icon name="refresh" size={14} />
          Try again
        </button>
      </div>
    </article>
  )
}
