/**
 * "How AKILI works" as a full view.
 *
 * Everything on this page describes the system as the repository builds it: the
 * agent loop from docs/architecture.md, the trust classes from the agent
 * contract §3, and the request path that keeps the browser away from Binance.
 * It is documentation of real behaviour, not a feature list.
 */

import { Icon, type IconName } from '../ui/Icon'
import styles from './views.module.css'

const TRUST_CLASSES: Array<{ name: string; meaning: string }> = [
  { name: 'USER_INPUT', meaning: 'What you typed. Untrusted; echoed back, never acted on as an instruction.' },
  {
    name: 'MODEL_INTERPRETATION',
    meaning: 'What the model concluded. Advisory. The backend validates it and may reject it outright.',
  },
  {
    name: 'BINANCE_FACT',
    meaning: 'A figure AKILI read from Binance, with the instant it was read. The only source of market numbers.',
  },
  {
    name: 'APPLICATION_GENERATED',
    meaning: 'Identifiers AKILI creates itself, like a conversation id.',
  },
]

const PATH: Array<{ icon: IconName; label: string; detail: string }> = [
  { icon: 'user', label: 'You', detail: 'Type a message in this browser' },
  { icon: 'message', label: 'AKILI backend', detail: 'POST /api/v1/chat — the only chat endpoint' },
  { icon: 'info', label: 'Agent', detail: 'Interprets, and may request one read-only call' },
  { icon: 'shield', label: 'Capability layer', detail: 'Checks the request, then makes the call itself' },
  { icon: 'market', label: 'Binance', detail: 'Public market data, read server-side' },
]

export function InfoView() {
  return (
    <div className={styles.view}>
      <header className={styles.viewHeader}>
        <h1 className={styles.viewTitle}>How AKILI works</h1>
        <p className={styles.viewLead}>
          AKILI reasons about what you want and explains it. It is not the thing that executes —
          that separation is the point, not a limitation to be worked around.
        </p>
      </header>

      <section className={styles.section} aria-labelledby="path-heading">
        <h2 className={styles.sectionTitle} id="path-heading">
          Where your request goes
        </h2>
        <ol className={styles.path}>
          {PATH.map((step, index) => (
            <li key={step.label} className={styles.pathStep}>
              <span className={styles.pathIcon} aria-hidden>
                <Icon name={step.icon} size={15} />
              </span>
              <span className={styles.pathText}>
                <span className={styles.pathLabel}>{step.label}</span>
                <span className={styles.pathDetail}>{step.detail}</span>
              </span>
              {index < PATH.length - 1 ? (
                <span className={styles.pathArrow} aria-hidden>
                  <Icon name="chevron-down" size={14} />
                </span>
              ) : null}
            </li>
          ))}
        </ol>
        <p className={styles.sectionNote}>
          Your browser never talks to Binance and holds no Binance credential. Every market figure
          you see arrived through AKILI&rsquo;s backend.
        </p>
      </section>

      <section className={styles.section} aria-labelledby="trust-heading">
        <h2 className={styles.sectionTitle} id="trust-heading">
          Why AKILI labels its figures
        </h2>
        <p className={styles.sectionLead}>
          Each value AKILI returns carries a trust class, and the interface keeps them apart so a
          Binance figure is never confused with the model&rsquo;s words.
        </p>
        <dl className={styles.trustList}>
          {TRUST_CLASSES.map((entry) => (
            <div key={entry.name} className={styles.trustRow}>
              <dt className={styles.trustName}>{entry.name}</dt>
              <dd className={styles.trustMeaning}>{entry.meaning}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className={styles.section} aria-labelledby="limits-heading">
        <h2 className={styles.sectionTitle} id="limits-heading">
          What this build cannot do
        </h2>
        <ul className={styles.limits}>
          <li>
            <strong>No orders.</strong> There is no planning, validation, approval, or execution
            path. AKILI cannot buy, sell, or transfer anything, and it will never tell you it has.
          </li>
          <li>
            <strong>No account access.</strong> The Binance connection stops at authorization, so
            balances, holdings, and order history are unknown and are not displayed.
          </li>
          <li>
            <strong>No AKILI login.</strong> Sign-up and sessions are a later milestone. In
            development the backend serves one fixed user.
          </li>
          <li>
            <strong>No market overview.</strong> AKILI reads one pair at a time, when you ask. There
            is no top-coins, gainers, or losers feed behind it.
          </li>
        </ul>
      </section>
    </div>
  )
}
