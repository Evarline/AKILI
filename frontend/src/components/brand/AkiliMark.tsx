/**
 * The AKILI mark: a geometric brain.
 *
 * Construction — a rotated rounded square, which is Binance's diamond geometry
 * used as a *language* rather than as a logo, cut through by a vertical fissure
 * into two hemispheres, each grooved with a folded gyrus. Nothing here is the
 * Binance mark, and the Binance mark is never set beside the word AKILI as a
 * substitute for one.
 *
 * The cuts are a mask rather than black strokes, so the mark sits correctly on
 * any surface: the grooves show whatever is behind them. It is one solid shape
 * with three cuts, which is what keeps it legible down to 16px where a
 * line-drawn version of the same idea turns to mush.
 *
 * `public/akili-mark.svg` is the same drawing, for the favicon.
 */

import { useId } from 'react'

type AkiliMarkProps = {
  /** Rendered width and height in px. */
  size?: number
  /** When set, the mark is announced to assistive technology; otherwise hidden. */
  title?: string
  className?: string | undefined
}

export const AKILI_TEAL = '#19B5A5'

export function AkiliMark({ size = 28, title, className }: AkiliMarkProps) {
  // Unique per instance: several marks share a page, and duplicate mask ids
  // would make every one of them use the first mask.
  const maskId = useId()

  return (
    <svg
      viewBox="0 0 32 32"
      width={size}
      height={size}
      className={className}
      {...(title
        ? { role: 'img' as const, 'aria-label': title }
        : { 'aria-hidden': true, focusable: false })}
    >
      <defs>
        <mask id={maskId}>
          {/* The body of the mark. */}
          <rect
            x="6"
            y="6"
            width="20"
            height="20"
            rx="4.5"
            transform="rotate(45 16 16)"
            fill="#fff"
          />
          {/* The cuts: the fissure down the centre, then one folded gyrus per
              hemisphere, each hooking back on itself twice. */}
          <g stroke="#000" strokeWidth="2.15" strokeLinecap="round" fill="none">
            <path d="M16 5.4V26.6" />
            <path d="M13.4 10.8C9 11.8 9 15.2 12.4 16 9 16.8 9 20.2 13.4 21.2" />
            <path d="M18.6 10.8C23 11.8 23 15.2 19.6 16 23 16.8 23 20.2 18.6 21.2" />
          </g>
        </mask>
      </defs>
      <rect width="32" height="32" fill={AKILI_TEAL} mask={`url(#${maskId})`} />
    </svg>
  )
}
