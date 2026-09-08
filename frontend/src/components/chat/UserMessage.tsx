/** One user turn: their own words, echoed back verbatim. */

import type { UserTurn } from '../../hooks/useChat'
import { formatClock } from '../../lib/time'
import { Icon } from '../ui/Icon'
import styles from './chat.module.css'

export function UserMessage({ turn }: { turn: UserTurn }) {
  return (
    <article className={styles.userRow} aria-label="Your message">
      <div className={styles.userBody}>
        <p className={styles.userBubble}>{turn.text}</p>
        <p className={styles.userTimestamp}>
          <time dateTime={new Date(turn.sentAt).toISOString()}>{formatClock(turn.sentAt)}</time>
        </p>
      </div>
      <span className={styles.userAvatar} aria-hidden>
        <Icon name="user" size={16} />
      </span>
    </article>
  )
}
