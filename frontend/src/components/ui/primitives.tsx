/**
 * Small shared primitives.
 *
 * `Unavailable` and `EmptyPanel` exist so that "the backend does not expose this
 * yet" has a first-class, honest presentation. Reaching for one of them is
 * always correct where the alternative would be inventing a value.
 */

import type { ReactNode } from 'react'
import { Icon, type IconName } from './Icon'
import styles from './ui.module.css'

export function Card({
  children,
  className,
}: {
  children: ReactNode
  className?: string | undefined
}) {
  return <div className={cx(styles.card, className)}>{children}</div>
}

export function RailCard({
  title,
  action,
  children,
  labelledBy,
}: {
  title: string
  action?: ReactNode | undefined
  children: ReactNode
  labelledBy?: string | undefined
}) {
  const headingId = labelledBy ?? `rail-${slug(title)}`
  return (
    <section className={styles.railCard} aria-labelledby={headingId}>
      <div className={styles.cardHeader}>
        <h2 className={styles.cardTitle} id={headingId}>
          {title}
        </h2>
        {action}
      </div>
      {children}
    </section>
  )
}

export function Pill({
  children,
  tone = 'default',
}: {
  children: ReactNode
  tone?: 'default' | 'emphasis' | 'warning'
}) {
  return (
    <span
      className={cx(
        styles.pill,
        tone === 'emphasis' && styles.pillEmphasis,
        tone === 'warning' && styles.pillWarning,
      )}
    >
      {children}
    </span>
  )
}

/**
 * A status dot with its meaning in words beside it. The text is not optional:
 * status is never communicated by colour alone.
 */
export function Status({
  tone,
  children,
}: {
  tone: 'up' | 'down' | 'warn' | 'idle'
  children: ReactNode
}) {
  const toneClass =
    tone === 'up'
      ? styles.dotUp
      : tone === 'down'
        ? styles.dotDown
        : tone === 'warn'
          ? styles.dotWarn
          : styles.dotIdle
  return (
    <span className={styles.status}>
      <span className={cx(styles.dot, toneClass)} aria-hidden />
      <span>{children}</span>
    </span>
  )
}

export function Button({
  children,
  onClick,
  variant = 'default',
  block = false,
  disabled = false,
  type = 'button',
  ariaLabel,
}: {
  children: ReactNode
  onClick?: (() => void) | undefined
  variant?: 'default' | 'primary'
  block?: boolean
  disabled?: boolean
  type?: 'button' | 'submit'
  ariaLabel?: string | undefined
}) {
  return (
    <button
      type={type}
      className={cx(
        styles.button,
        variant === 'primary' && styles.buttonPrimary,
        block && styles.buttonBlock,
      )}
      onClick={onClick}
      disabled={disabled}
      {...(ariaLabel ? { 'aria-label': ariaLabel } : {})}
    >
      {children}
    </button>
  )
}

/**
 * "AKILI cannot show this yet", said plainly.
 *
 * `hint` is where the concrete reason goes — which backend phase owns the
 * feature, or which setting turns it on — so the state is informative rather
 * than a dead end.
 */
export function Unavailable({
  icon = 'info',
  title,
  children,
}: {
  icon?: IconName
  title: string
  children?: ReactNode
}) {
  return (
    <div className={styles.notice}>
      <p className={styles.noticeTitle}>
        <Icon name={icon} size={15} />
        {title}
      </p>
      {children ? <div className={styles.noticeBody}>{children}</div> : null}
    </div>
  )
}

export function Code({ children }: { children: ReactNode }) {
  return <code className={styles.noticeCode}>{children}</code>
}

/**
 * The trust class of what is being shown, in the backend's own vocabulary
 * (`BINANCE_FACT`, `MODEL_INTERPRETATION`). Rendered from the response's own
 * `provenance` field, so a caller can always tell a Binance figure from the
 * model's words.
 */
export function ProvenanceLabel({ children }: { children: ReactNode }) {
  return <span className={styles.provenance}>{children}</span>
}

export function Divider() {
  return <hr className={styles.divider} />
}

export function cx(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(' ')
}

function slug(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-')
}
