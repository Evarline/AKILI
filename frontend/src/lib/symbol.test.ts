import { describe, expect, it } from 'vitest'
import { assetMonogram, formatPair, splitSymbol } from './symbol'

describe('symbol presentation', () => {
  it('splits a pair only against known quote assets, longest first', () => {
    expect(splitSymbol('BTCUSDT')).toEqual({ base: 'BTC', quote: 'USDT', raw: 'BTCUSDT' })
    expect(splitSymbol('ETHBTC')).toEqual({ base: 'ETH', quote: 'BTC', raw: 'ETHBTC' })
    expect(splitSymbol('1INCHUSDT').base).toBe('1INCH')
  })

  it('leaves an unrecognised symbol alone rather than guessing a split', () => {
    expect(splitSymbol('WEIRDPAIR')).toEqual({ base: null, quote: null, raw: 'WEIRDPAIR' })
    expect(formatPair('WEIRDPAIR')).toBe('WEIRDPAIR')
  })

  it('formats a recognised pair for display', () => {
    expect(formatPair('BTCUSDT')).toBe('BTC / USDT')
  })

  it('builds an avatar from the real symbol, never from a logo mapping', () => {
    expect(assetMonogram('BTCUSDT')).toBe('BTC')
    expect(assetMonogram('WEIRDPAIR')).toBe('WEI')
  })
})
