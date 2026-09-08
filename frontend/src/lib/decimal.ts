/**
 * Formatting for the decimal strings the backend sends.
 *
 * Binance transmits prices as strings so that no float rounding occurs, and the
 * backend preserves that exactness with `Decimal`. These helpers therefore work
 * on the *string* — grouping the integer part and trimming trailing zeros —
 * and never call `parseFloat` on a value that will be shown to the user. A
 * displayed figure is the backend's figure, digit for digit.
 *
 * `Number()` appears in exactly one place, `toPlotNumber`, which is only ever
 * used for chart geometry (pixel coordinates), never for a displayed value.
 */

type ParsedDecimal = {
  sign: '' | '-'
  integer: string
  fraction: string
}

/** Split a decimal string into sign / integer / fraction, or null if malformed. */
export function parseDecimalString(value: string): ParsedDecimal | null {
  const trimmed = value.trim()
  if (!/^[+-]?\d*\.?\d+$/.test(trimmed)) return null

  const sign = trimmed.startsWith('-') ? '-' : ''
  const unsigned = trimmed.replace(/^[+-]/, '')
  const [rawInteger = '', rawFraction = ''] = unsigned.split('.')

  return {
    sign,
    integer: rawInteger.replace(/^0+(?=\d)/, '') || '0',
    fraction: rawFraction,
  }
}

function group(integer: string): string {
  return integer.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

export type FormatDecimalOptions = {
  /** Pad the fraction out to this many digits. */
  minFractionDigits?: number
  /** Truncate — never round — the fraction to at most this many digits. */
  maxFractionDigits?: number
  /** Thousands separators on the integer part. Default true. */
  grouping?: boolean
}

/**
 * Format a decimal string for display.
 *
 * Truncates rather than rounds when `maxFractionDigits` is exceeded, so the UI
 * can never show a figure larger than the one Binance reported. Returns the
 * input unchanged if it is not a decimal string: an unexpected shape is shown
 * as-is rather than silently replaced by something invented.
 */
export function formatDecimal(value: string, options: FormatDecimalOptions = {}): string {
  const parsed = parseDecimalString(value)
  if (parsed === null) return value

  const { minFractionDigits = 0, maxFractionDigits, grouping = true } = options
  let fraction = parsed.fraction
  if (maxFractionDigits !== undefined) fraction = fraction.slice(0, maxFractionDigits)
  fraction = fraction.padEnd(minFractionDigits, '0')

  const integer = grouping ? group(parsed.integer) : parsed.integer
  return fraction ? `${parsed.sign}${integer}.${fraction}` : `${parsed.sign}${integer}`
}

/**
 * Format a price the way a financial product does: two decimals for anything
 * over 1, more precision for the small ones, and never more digits than the
 * backend actually sent.
 */
export function formatPrice(value: string): string {
  const parsed = parseDecimalString(value)
  if (parsed === null) return value

  const magnitude = parsed.integer.replace(/^0$/, '').length
  const maxFractionDigits = magnitude >= 1 ? 2 : parsed.fraction.length > 0 ? 8 : 0
  return formatDecimal(value, { minFractionDigits: magnitude >= 1 ? 2 : 0, maxFractionDigits })
}

/** A signed percentage, e.g. "+2.34%" / "-0.51%". Two decimals, truncated. */
export function formatPercent(value: string): string {
  const parsed = parseDecimalString(value)
  if (parsed === null) return value
  const body = formatDecimal(value, { minFractionDigits: 2, maxFractionDigits: 2 })
  return `${isPositive(value) ? '+' : ''}${body}%`
}

/** A signed absolute change, e.g. "+1,204.11". */
export function formatSignedPrice(value: string): string {
  const body = formatPrice(value)
  return isPositive(value) ? `+${body}` : body
}

/**
 * Compact volume: 28.4B, 912.5M, 4.1K. Derived from the digit count of the
 * integer part, so no float is involved in choosing or producing the figure.
 */
export function formatCompact(value: string): string {
  const parsed = parseDecimalString(value)
  if (parsed === null) return value

  const digits = parsed.integer
  const units: Array<[number, string]> = [
    [13, 'T'],
    [10, 'B'],
    [7, 'M'],
    [4, 'K'],
  ]
  for (const [threshold, suffix] of units) {
    if (digits.length >= threshold) {
      const whole = digits.slice(0, digits.length - (threshold - 1))
      const rest = digits.slice(digits.length - (threshold - 1), digits.length - (threshold - 2))
      return `${parsed.sign}${group(whole)}${rest ? `.${rest}` : ''}${suffix}`
    }
  }
  return formatDecimal(value, { maxFractionDigits: 2 })
}

/** Sign of a decimal string, by inspecting digits. Zero counts as neither. */
export function decimalSign(value: string): 1 | 0 | -1 {
  const parsed = parseDecimalString(value)
  if (parsed === null) return 0
  const isZero = /^0*$/.test(parsed.integer) && /^0*$/.test(parsed.fraction)
  if (isZero) return 0
  return parsed.sign === '-' ? -1 : 1
}

export function isPositive(value: string): boolean {
  return decimalSign(value) > 0
}

/**
 * A decimal string as a number, **for chart geometry only**.
 *
 * Candle coordinates are pixels, so float precision is irrelevant there. Never
 * use this for a figure the user reads — that is what `formatDecimal` is for.
 */
export function toPlotNumber(value: string): number {
  const asNumber = Number(value)
  return Number.isFinite(asNumber) ? asNumber : 0
}
