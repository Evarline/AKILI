/**
 * The state AKILI opens in.
 *
 * Static UI copy and a real clock — and nothing else. There is no example
 * conversation beneath it, no suggested-prompt row that would look like history,
 * no price, and no portfolio figure. The interface fills up only when the user
 * says something and the backend answers.
 *
 * The capability list is not decoration: it is the closed set of intents in
 * `app.agent.schemas.Intent`, so it tells the user exactly what this build can
 * and cannot do rather than implying more.
 */

import { greetingForHour } from '../../lib/time'
import { AkiliMark } from '../brand/AkiliMark'
import { Icon, type IconName } from '../ui/Icon'
import styles from './chat.module.css'

const CAPABILITIES: Array<{ icon: IconName; title: string; body: string }> = [
  {
    icon: 'market',
    title: 'Read live market data',
    body: 'Current price, 24-hour change, and recent candles for a Spot pair — fetched from Binance by AKILI, never guessed.',
  },
  {
    icon: 'info',
    title: 'Explain how things work',
    body: 'Plain answers to beginner questions, like what a market order is or how Spot trading differs from futures.',
  },
  {
    icon: 'check',
    title: 'Interpret a purchase',
    body: 'Work out the asset and amount you mean. AKILI stops there: it does not price, plan, approve, or place orders.',
  },
]

export function EmptyState() {
  return (
    <div className={styles.empty}>
      <span className={styles.emptyMark}>
        <AkiliMark size={44} title="AKILI" />
      </span>

      <h1 className={styles.emptyGreeting}>{greetingForHour()} 👋</h1>
      <p className={styles.emptyLead}>I&rsquo;m AKILI, your Binance AI agent.</p>
      <p className={styles.emptyPrompt}>What would you like to do?</p>

      <ul className={styles.capabilities}>
        {CAPABILITIES.map((capability) => (
          <li key={capability.title} className={styles.capability}>
            <span className={styles.capabilityIcon} aria-hidden>
              <Icon name={capability.icon} size={16} />
            </span>
            <div>
              <p className={styles.capabilityTitle}>{capability.title}</p>
              <p className={styles.capabilityBody}>{capability.body}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
