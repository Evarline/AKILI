import { describe, expect, it } from 'vitest'
import {
  decimalSign,
  formatCompact,
  formatDecimal,
  formatPercent,
  formatPrice,
  formatSignedPrice,
} from './decimal'

describe('decimal-string formatting', () => {
  it('keeps every digit the backend sent', () => {
    // A price with more precision than a double can hold exactly. It must come
    // out unchanged, because the backend sent it exactly.
    expect(formatDecimal('12345678901234567890.12345678901234567890')).toBe(
      '12,345,678,901,234,567,890.12345678901234567890',
    )
  })

  it('truncates rather than rounds, so a figure is never inflated', () => {
    expect(formatDecimal('0.999999', { maxFractionDigits: 2 })).toBe('0.99')
    expect(formatPrice('64188.999')).toBe('64,188.99')
  })

  it('formats prices with two decimals above 1 and more precision below', () => {
    expect(formatPrice('64188.4')).toBe('64,188.40')
    expect(formatPrice('0.00017979')).toBe('0.00017979')
  })

  it('signs percentages and absolute changes', () => {
    expect(formatPercent('1.91')).toBe('+1.91%')
    expect(formatPercent('-0.5')).toBe('-0.50%')
    expect(formatPercent('0')).toBe('0.00%')
    expect(formatSignedPrice('1204.11')).toBe('+1,204.11')
    expect(formatSignedPrice('-1204.11')).toBe('-1,204.11')
  })

  it('reads the sign from the digits, not from a float', () => {
    expect(decimalSign('0.0000')).toBe(0)
    expect(decimalSign('-0.0001')).toBe(-1)
    expect(decimalSign('0.0001')).toBe(1)
  })

  it('compacts volumes without a float', () => {
    expect(formatCompact('28412000000')).toBe('28.4B')
    expect(formatCompact('912500000')).toBe('912.5M')
    expect(formatCompact('4100')).toBe('4.1K')
    expect(formatCompact('812.44')).toBe('812.44')
  })

  it('returns an unexpected shape unchanged instead of inventing a number', () => {
    expect(formatDecimal('not-a-number')).toBe('not-a-number')
    expect(formatPrice('')).toBe('')
  })
})
