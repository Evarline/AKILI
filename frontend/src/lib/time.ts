/**
 * Time formatting for the one timestamp the backend actually sends:
 * `market_data.observed_at`, the moment AKILI read the data from Binance.
 *
 * The reference shows "Observed just now". That phrasing is only honest when it
 * is derived from a real instant, so it is computed from `observed_at` here and
 * degrades to an explicit clock time as the reading ages — market data is a
 * reading, never a live feed.
 */

const MINUTE = 60_000
const HOUR = 60 * MINUTE
const DAY = 24 * HOUR

/** Relative age of an ISO-8601 instant: "just now", "3 min ago", "2h ago". */
export function formatObservedAge(isoInstant: string, now: number = Date.now()): string {
  const observed = Date.parse(isoInstant)
  if (Number.isNaN(observed)) return 'time unknown'

  const elapsed = now - observed
  if (elapsed < 0) return 'just now'
  if (elapsed < 45_000) return 'just now'
  if (elapsed < HOUR) return `${Math.floor(elapsed / MINUTE)} min ago`
  if (elapsed < DAY) return `${Math.floor(elapsed / HOUR)}h ago`
  return `${Math.floor(elapsed / DAY)}d ago`
}

/** The absolute instant, for the tooltip behind the relative age. */
export function formatAbsolute(isoInstant: string): string {
  const observed = new Date(isoInstant)
  if (Number.isNaN(observed.getTime())) return isoInstant
  return observed.toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'medium',
  })
}

/** Wall-clock time of a message, e.g. "7:24 PM". */
export function formatClock(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  })
}

/** "2h ago" for a locally-tracked instant, used by the conversation list. */
export function formatRelative(timestamp: number, now: number = Date.now()): string {
  const elapsed = now - timestamp
  if (elapsed < MINUTE) return 'just now'
  if (elapsed < HOUR) return `${Math.floor(elapsed / MINUTE)}m ago`
  if (elapsed < DAY) return `${Math.floor(elapsed / HOUR)}h ago`
  return `${Math.floor(elapsed / DAY)}d ago`
}

/** Which part of the day it is, for the greeting. Static copy, real clock. */
export function greetingForHour(hour: number = new Date().getHours()): string {
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}
