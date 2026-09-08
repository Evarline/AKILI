/**
 * A candlestick sparkline drawn from the real `klines` the backend fetched.
 *
 * Every candle is one `Kline` from `market_data.klines`; the component renders
 * nothing at all when that array is empty. Green and red mean close above or
 * below open — the direction of a real move, and the only thing colour is
 * carrying here. The chart is `aria-hidden` because it is a redrawing of data
 * that is also stated in text; the surrounding card names the interval and the
 * candle count for anyone not looking at it.
 */

import { toPlotNumber } from '../../lib/decimal'
import type { Kline } from '../../types/contract'
import styles from './market.module.css'

const WIDTH = 200
const HEIGHT = 64
const PADDING_Y = 4

export function CandleChart({ klines, height = HEIGHT }: { klines: Kline[]; height?: number }) {
  if (klines.length === 0) return null

  const highs = klines.map((candle) => toPlotNumber(candle.high_price))
  const lows = klines.map((candle) => toPlotNumber(candle.low_price))
  const max = Math.max(...highs)
  const min = Math.min(...lows)
  const span = max - min || 1

  const slot = WIDTH / klines.length
  const bodyWidth = Math.max(1.5, Math.min(6, slot * 0.62))
  const plotHeight = height - PADDING_Y * 2
  const y = (value: number) => PADDING_Y + ((max - value) / span) * plotHeight

  return (
    <svg
      className={styles.chart}
      viewBox={`0 0 ${WIDTH} ${height}`}
      preserveAspectRatio="none"
      aria-hidden
    >
      {klines.map((candle, index) => {
        const open = toPlotNumber(candle.open_price)
        const close = toPlotNumber(candle.close_price)
        const rising = close >= open
        const centre = index * slot + slot / 2
        const bodyTop = y(Math.max(open, close))
        const bodyBottom = y(Math.min(open, close))
        const colour = rising ? 'var(--up)' : 'var(--down)'

        return (
          <g key={candle.open_time}>
            <line
              x1={centre}
              x2={centre}
              y1={y(toPlotNumber(candle.high_price))}
              y2={y(toPlotNumber(candle.low_price))}
              stroke={colour}
              strokeWidth={1}
            />
            <rect
              x={centre - bodyWidth / 2}
              y={bodyTop}
              width={bodyWidth}
              height={Math.max(1, bodyBottom - bodyTop)}
              fill={colour}
              rx={0.5}
            />
          </g>
        )
      })}
    </svg>
  )
}
