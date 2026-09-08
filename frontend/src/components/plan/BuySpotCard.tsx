/**
 * What AKILI understood about a purchase — and, just as importantly, what it has
 * not done.
 *
 * The backend's BUY_SPOT response carries exactly three slots
 * (`app.agent.schemas.BuySpotParameters`): the asset as the user named it, the
 * amount as a decimal string, and the currency they expressed it in. That is
 * MODEL INTERPRETATION, and it is all there is.
 *
 * There is **no** TradingPlan in the contract yet. No resolved trading pair, no
 * market price for the purchase, no estimated quantity, no fee — planning,
 * validation, approval, and execution are later backend milestones. So this card
 * renders the three real slots and then states plainly that no plan exists,
 * rather than filling the reference design's plan rows with numbers AKILI was
 * never given.
 *
 * The NOT EXECUTED status is unconditional here. It cannot become anything else
 * until a real execution result exists in the contract to make it so.
 */

import { formatDecimal } from '../../lib/decimal'
import type { BuySpotParameters } from '../../types/contract'
import { Icon } from '../ui/Icon'
import { Pill, ProvenanceLabel, cx } from '../ui/primitives'
import styles from './plan.module.css'

export function BuySpotCard({
  parameters,
  requiresClarification,
}: {
  parameters: BuySpotParameters
  requiresClarification: boolean
}) {
  const { asset, quote_amount, quote_currency } = parameters
  const heading = asset ? `Buy ${asset}` : 'Buy request'

  return (
    <section className={styles.card} aria-label={`${heading} — not executed`}>
      <header className={styles.header}>
        <div>
          <h3 className={styles.heading}>{heading}</h3>
          <p className={styles.subheading}>What AKILI understood from your message</p>
        </div>
        {/* Unconditional: nothing in this milestone can execute an order. */}
        <Pill tone="warning">NOT EXECUTED</Pill>
      </header>

      <dl className={styles.slots}>
        <Slot label="Asset" value={asset} missing="not stated yet" />
        <Slot
          label="Amount"
          value={
            quote_amount === null
              ? null
              : `${formatDecimal(quote_amount, { maxFractionDigits: 8 })}${
                  quote_currency ? ` ${quote_currency}` : ''
                }`
          }
          missing="not stated yet"
        />
        {/* Only shown when the user actually named a currency; never defaulted
            to USDT, because the backend does not convert or assume one. */}
        {quote_currency ? <Slot label="Currency as stated" value={quote_currency} /> : null}
      </dl>

      {requiresClarification ? (
        <p className={styles.pending}>
          AKILI still needs one more detail before this can go any further.
        </p>
      ) : (
        <div className={styles.planNotice}>
          <Icon name="info" size={15} className={styles.planIcon} />
          <div>
            <p className={styles.planTitle}>Trading plan — not generated yet</p>
            <p className={styles.planBody}>
              AKILI has interpreted your request, but it has not priced it, resolved a
              trading pair, estimated a quantity, or validated anything. Planning,
              validation, approval, and execution are not part of this build, so no
              order exists and none can be placed.
            </p>
          </div>
        </div>
      )}

      <footer className={styles.footer}>
        <ProvenanceLabel>MODEL_INTERPRETATION</ProvenanceLabel>
        <span className={styles.footerNote}>Interpreted from your words — not a quote</span>
      </footer>
    </section>
  )
}

function Slot({
  label,
  value,
  missing,
}: {
  label: string
  value: string | null
  missing?: string
}) {
  return (
    <div className={styles.slot}>
      <dt className={styles.slotLabel}>{label}</dt>
      <dd className={cx(styles.slotValue, value === null && styles.slotMissing, 'tabular')}>
        {value ?? missing ?? '—'}
      </dd>
    </div>
  )
}
