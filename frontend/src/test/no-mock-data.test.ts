/**
 * Guards on the rules that matter most, enforced against the source itself.
 *
 * These are the checks that would otherwise depend on someone remembering:
 *
 *   1. The frontend never addresses Binance. Every market figure arrives through
 *      AKILI's backend, so a Binance host or an API-key reference in `src/`
 *      would mean the architecture had been bypassed.
 *   2. No credential is read from the environment or written to storage.
 *   3. Application code holds no market prices, balances, or seeded
 *      conversations. Test doubles live in `src/test/` and are excluded, which
 *      is what makes the rest checkable.
 *   4. The UI never claims an execution.
 */

import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { describe, expect, it } from 'vitest'

const SRC = join(process.cwd(), 'src')

function sourceFiles(dir: string = SRC): string[] {
  return readdirSync(dir).flatMap((entry) => {
    const path = join(dir, entry)
    if (statSync(path).isDirectory()) return sourceFiles(path)
    return /\.(ts|tsx|css)$/.test(path) ? [path] : []
  })
}

/**
 * This file is excluded from every scan below: it has to name the forbidden
 * hosts and patterns in order to look for them, and matching itself would make
 * the guards permanently red.
 */
const SELF = join(SRC, 'test', 'no-mock-data.test.ts')

const SCANNED_FILES = sourceFiles().filter((path) => path !== SELF)

/** Application code: everything except the tests and their fixtures. */
const APPLICATION_FILES = SCANNED_FILES.filter(
  (path) => !path.includes(join('src', 'test')) && !/\.test\.tsx?$/.test(path),
)

function read(path: string): string {
  return readFileSync(path, 'utf8')
}

function label(path: string): string {
  return relative(process.cwd(), path)
}

describe('the browser never talks to Binance', () => {
  it('names no Binance host anywhere in src/', () => {
    // The architecture is Frontend -> AKILI backend -> ... -> Binance. A
    // Binance hostname here would mean the browser had been pointed at it.
    const forbidden = [
      'api.binance.com',
      'api1.binance.com',
      'fapi.binance.com',
      'dapi.binance.com',
      'stream.binance.com',
      'testnet.binance',
      'agent.binance.com',
    ]

    for (const path of SCANNED_FILES) {
      const contents = read(path)
      for (const host of forbidden) {
        expect(contents, `${label(path)} must not address ${host} directly`).not.toContain(host)
      }
    }
  })

  it('references no Binance credential or signing primitive', () => {
    const forbidden = [/BINANCE_API_KEY/, /X-MBX-APIKEY/i, /binanceSecret/i, /hmac/i, /createHmac/]

    for (const path of SCANNED_FILES) {
      const contents = read(path)
      for (const pattern of forbidden) {
        expect(contents, `${label(path)} must not carry a Binance credential`).not.toMatch(pattern)
      }
    }
  })
})

describe('no secret reaches the browser', () => {
  it('reads only VITE_API_BASE_URL from the environment', () => {
    const envReads = new Set<string>()
    for (const path of SCANNED_FILES) {
      for (const match of read(path).matchAll(/import\.meta\.env\[?['"`]?(VITE_\w+)/g)) {
        if (match[1]) envReads.add(match[1])
      }
    }
    expect([...envReads].sort()).toEqual(['VITE_API_BASE_URL'])
  })

  it('never writes to localStorage or sessionStorage', () => {
    for (const path of APPLICATION_FILES) {
      const contents = read(path)
      expect(contents, `${label(path)} must not use localStorage`).not.toContain('localStorage')
      expect(contents, `${label(path)} must not use sessionStorage`).not.toContain('sessionStorage')
    }
  })
})

describe('no mock application data', () => {
  it('hard-codes no market price, balance, or portfolio value', () => {
    // A currency-shaped string literal: "$111,240.50", '$12,450'.
    const currencyLiteral = /['"`]\s*\$\s?\d[\d,]*(\.\d+)?\s*['"`]/
    // A price-shaped numeric or string literal: four or more integer digits
    // with a two-decimal fraction. Deliberately narrower than "any big
    // number", so a real constant such as a max message length is not flagged
    // while an invented price is.
    const priceShaped = /(?<![\w.])\d{4,}\.\d{2}(?![\d\w])/

    for (const path of APPLICATION_FILES) {
      if (path.endsWith('.css')) continue
      const contents = read(path)
      expect(contents, `${label(path)} must not hard-code a currency figure`).not.toMatch(
        currencyLiteral,
      )
      expect(contents, `${label(path)} must not hard-code a price-shaped value`).not.toMatch(
        priceShaped,
      )
    }
  })

  it('seeds no conversation, message, ticker, or kline', () => {
    // A seeded array is one whose first element is a literal — `[{`, `['`,
    // `[1`. An array built from existing state (`[...turns, next]`) is real
    // data being extended and is not matched.
    const seeded =
      /(?:const|let)\s+(?:messages|conversations|turns|marketData|markets|topCoins|gainers|losers|portfolio|balances|holdings|trades|klines|tickers|plans)\s*(?::[^=]+)?=\s*\[\s*[{'"`\d]/

    for (const path of APPLICATION_FILES) {
      if (path.endsWith('.css')) continue
      expect(read(path), `${label(path)} must not seed application data`).not.toMatch(seeded)
    }
  })
})

describe('AKILI never claims an execution', () => {
  it('contains no success-of-execution copy', () => {
    const forbidden = [
      /order placed/i,
      /trade executed/i,
      /purchase successful/i,
      /order filled/i,
      /successfully bought/i,
      /transaction complete/i,
    ]

    for (const path of APPLICATION_FILES) {
      const contents = read(path)
      for (const pattern of forbidden) {
        expect(contents, `${label(path)} must not claim an execution`).not.toMatch(pattern)
      }
    }
  })

  it('states NOT EXECUTED on the BUY_SPOT card', () => {
    const card = read(join(SRC, 'components', 'plan', 'BuySpotCard.tsx'))
    expect(card).toContain('NOT EXECUTED')
  })
})

describe('there is exactly one chat endpoint', () => {
  it('declares the chat path in exactly one place', () => {
    // The path is named in prose in a few components (it is worth telling the
    // user which endpoint answers them), so what is asserted is that there is
    // one route constant, defined once, rather than one mention.
    const declarations = APPLICATION_FILES.filter((path) =>
      /export const CHAT_PATH\s*=/.test(read(path)),
    )
    expect(declarations.map(label)).toEqual(['src/api/chat.ts'])

    const senders = APPLICATION_FILES.filter((path) => /sendChatMessage\s*\(/.test(read(path)))
    expect(senders.map(label).sort()).toEqual(['src/api/chat.ts', 'src/hooks/useChat.ts'])
  })

  it('routes every request through the one client module', () => {
    // `fetch` belongs to src/api/client.ts alone; a component calling it
    // directly would be a second, unaudited path out of the browser.
    const fetchers = APPLICATION_FILES.filter((path) => /\bfetch\(/.test(read(path)))
    expect(fetchers.map(label)).toEqual(['src/api/client.ts'])
  })
})
