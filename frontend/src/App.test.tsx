/**
 * The end-to-end experience, with `fetch` stubbed at the boundary.
 *
 * Nothing below asserts on invented behaviour: every stubbed response is the
 * shape `backend/app/api/chat.py` actually returns, and every asserted failure
 * is a status one of the backend's handlers actually produces.
 */

import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import {
  chatResponse,
  interpretation,
  jsonResponse,
  kline,
  marketDataFacts,
  stubFetch,
} from './test/fixtures'

const HEALTH = () => jsonResponse({ status: 'ok', version: '0.1.0' })
/** Direct Binance account access is unavailable unless backend credentials are configured. */
const BINANCE_DISABLED = () => jsonResponse({ detail: 'Not found' }, 404)

function mount(routes: Record<string, () => Response | Promise<Response>>) {
  const fetchStub = stubFetch({
    '/health': HEALTH,
    '/api/v1/binance/connection': BINANCE_DISABLED,
    ...routes,
  })
  vi.stubGlobal('fetch', fetchStub)
  render(<App />)
  return fetchStub
}

/** The (url, init) pair of the nth chat call. */
function chatCall(stub: ReturnType<typeof stubFetch>, index: number): RequestInit {
  const calls = stub.mock.calls.filter(([url]) => String(url).includes('/api/v1/chat'))
  const call = calls[index]
  if (!call) throw new Error(`no chat call at index ${index}`)
  return (call as unknown as [string, RequestInit])[1]
}

async function send(message: string) {
  const composer = screen.getByLabelText('Message AKILI')
  await userEvent.type(composer, message)
  await userEvent.click(screen.getByRole('button', { name: 'Send message' }))
}

beforeEach(() => {
  vi.useRealTimers()
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('the state AKILI opens in', () => {
  it('shows a welcome and an empty conversation, with no seeded turns', () => {
    mount({})

    expect(screen.getByRole('heading', { level: 1, name: /Good (morning|afternoon|evening)/ }))
      .toBeInTheDocument()
    expect(screen.getByText(/I’m AKILI, your Binance AI agent\./)).toBeInTheDocument()

    // No conversation turns exist before the user has said anything.
    expect(screen.queryByLabelText('Your message')).not.toBeInTheDocument()
    expect(screen.queryByLabelText("AKILI's reply")).not.toBeInTheDocument()
    expect(screen.getByText(/No conversations yet/)).toBeInTheDocument()
  })

  it('shows no market figure and no portfolio value', async () => {
    mount({})

    expect(screen.getByText('No market data read yet')).toBeInTheDocument()
    // The portfolio card is present but explicitly empty, never a total.
    expect(screen.getByText('Not available yet')).toBeInTheDocument()
    expect(screen.queryByText(/\$\d/)).not.toBeInTheDocument()

    await waitFor(() => expect(screen.getByText('Not configured')).toBeInTheDocument())
  })
})

describe('a real chat turn', () => {
  it('posts the message to /api/v1/chat and renders the backend’s own answer', async () => {
    const fetchStub = mount({
      '/api/v1/chat': () =>
        jsonResponse(
          chatResponse({
            response: interpretation({
              message: 'A market order buys at whatever price is available right now.',
            }),
          }),
        ),
    })

    await send('What is a market order?')

    // The user's own words, echoed verbatim.
    expect(within(screen.getByLabelText('Your message')).getByText('What is a market order?')).toBeInTheDocument()

    await waitFor(() =>
      expect(
        screen.getByText('A market order buys at whatever price is available right now.'),
      ).toBeInTheDocument(),
    )

    const init = chatCall(fetchStub, 0)
    expect(init.method).toBe('POST')
    expect(JSON.parse(String(init.body))).toEqual({ message: 'What is a market order?' })
  })

  it('continues the conversation with the id the backend returned', async () => {
    const fetchStub = mount({
      '/api/v1/chat': () => jsonResponse(chatResponse()),
    })

    await send('First question')
    await waitFor(() => expect(screen.getByLabelText("AKILI's reply")).toBeInTheDocument())
    await send('Second question')

    await waitFor(() => {
      expect(
        fetchStub.mock.calls.filter(([url]) => String(url).includes('/api/v1/chat')),
      ).toHaveLength(2)
      expect(JSON.parse(String(chatCall(fetchStub, 1).body))).toEqual({
        message: 'Second question',
        conversation_id: '11111111-1111-4111-8111-111111111111',
      })
    })
  })

  it('shows a loading state while the turn is in flight, with nothing beneath it', async () => {
    let release: (value: Response) => void = () => {}
    mount({
      '/api/v1/chat': () => new Promise<Response>((resolve) => (release = resolve)),
    })

    await send('What is BTC worth?')

    expect(await screen.findByText('AKILI is thinking')).toBeInTheDocument()
    // No card, no figure, no placeholder answer during the wait.
    expect(screen.queryByLabelText(/Market data for/)).not.toBeInTheDocument()

    release(jsonResponse(chatResponse()))
    await waitFor(() => expect(screen.queryByText('AKILI is thinking')).not.toBeInTheDocument())
  })
})

describe('real market data', () => {
  it('renders only the ticker fields the backend sent', async () => {
    mount({
      '/api/v1/chat': () =>
        jsonResponse(
          chatResponse({
            response: interpretation({
              intent: 'MARKET_INFORMATION',
              message: 'Here is the current Bitcoin price.',
            }),
            market_data: marketDataFacts(),
          }),
        ),
    })

    await send('What is the current BTC price?')

    const card = await screen.findByLabelText('Market data for BTCUSDT')
    expect(within(card).getByText('BTC / USDT')).toBeInTheDocument()
    expect(within(card).getByText('64,188.42')).toBeInTheDocument()
    expect(within(card).getByText(/\+1\.91%/)).toBeInTheDocument()
    expect(within(card).getByText('64,990.00')).toBeInTheDocument()
    expect(within(card).getByText('62,710.53')).toBeInTheDocument()
    expect(within(card).getByText('28.4B')).toBeInTheDocument()

    // Provenance and the observation instant are always stated.
    expect(within(card).getByText('BINANCE_FACT')).toBeInTheDocument()
    expect(within(card).getByText(/Observed/)).toBeInTheDocument()

    // Fields the backend does not send must not appear.
    expect(within(card).queryByText(/market cap/i)).not.toBeInTheDocument()
    expect(within(card).queryByText(/Bitcoin$/)).not.toBeInTheDocument()
  })

  it('shows no price line for a klines reading, because none was fetched', async () => {
    mount({
      '/api/v1/chat': () =>
        jsonResponse(
          chatResponse({
            response: interpretation({
              intent: 'MARKET_INFORMATION',
              message: 'Here is how BTC has moved recently.',
            }),
            market_data: marketDataFacts({
              capability: 'get_klines',
              interval: '1h',
              ticker: null,
              klines: [kline(), kline({ open_time: '2026-09-08T11:00:00+00:00' })],
            }),
          }),
        ),
    })

    await send('How has BTC moved today?')

    const card = await screen.findByLabelText('Market data for BTCUSDT')
    expect(within(card).getByText(/2 1h candles/)).toBeInTheDocument()
    expect(
      within(card).getByText(/This reading returned candles only — no current price was fetched\./),
    ).toBeInTheDocument()
    // No 24h stats row: `ticker` was null.
    expect(within(card).queryByText('24h High')).not.toBeInTheDocument()
  })
})

describe('BUY_SPOT', () => {
  it('shows the extracted slots, NOT EXECUTED, and no fabricated plan', async () => {
    mount({
      '/api/v1/chat': () =>
        jsonResponse(
          chatResponse({
            response: interpretation({
              intent: 'BUY_SPOT',
              message: 'I can help you plan that purchase.',
              parameters: { asset: 'BTC', quote_amount: '20', quote_currency: 'USD' },
            }),
          }),
        ),
    })

    await send('Buy $20 of BTC')

    const card = await screen.findByLabelText('Buy BTC — not executed')
    expect(within(card).getByText('NOT EXECUTED')).toBeInTheDocument()
    expect(within(card).getByText('20 USD')).toBeInTheDocument()
    expect(within(card).getByText('Trading plan — not generated yet')).toBeInTheDocument()

    // The reference design's plan rows are absent, because the backend sends no
    // market price, no resolved pair, and no estimated quantity for a purchase.
    expect(within(card).queryByText('Market price')).not.toBeInTheDocument()
    expect(within(card).queryByText('Estimated quantity')).not.toBeInTheDocument()
    expect(within(card).queryByText(/BTC\/USDT/)).not.toBeInTheDocument()
  })

  it('renders a clarifying question rather than filling in the missing slot', async () => {
    mount({
      '/api/v1/chat': () =>
        jsonResponse(
          chatResponse({
            response: interpretation({
              intent: 'BUY_SPOT',
              requires_clarification: true,
              message: 'I need one more detail.',
              question: 'How much would you like to spend?',
              parameters: { asset: 'BTC', quote_amount: null, quote_currency: null },
            }),
          }),
        ),
    })

    await send('Buy some BTC')

    expect(await screen.findByText('How much would you like to spend?')).toBeInTheDocument()
    const card = screen.getByLabelText('Buy BTC — not executed')
    expect(within(card).getByText('not stated yet')).toBeInTheDocument()
  })
})

describe('honest states for what the backend does not have', () => {
  it('says the account is not connected for ACCOUNT_INFORMATION', async () => {
    mount({
      '/api/v1/chat': () =>
        jsonResponse(
          chatResponse({
            response: interpretation({
              intent: 'ACCOUNT_INFORMATION',
              message: 'I cannot see your account yet.',
            }),
          }),
        ),
    })

    await send('What is my balance?')

    expect(await screen.findByText('Your Binance account is not connected')).toBeInTheDocument()
    // No balance figure of any kind.
    expect(screen.queryByText(/\$\d/)).not.toBeInTheDocument()
  })

  it('reports a successful server-side Binance account check', async () => {
    mount({
      '/api/v1/binance/connection': () =>
        jsonResponse({
          connected: true,
          credentials_configured: true,
          account_type: 'SPOT',
        }),
    })

    expect(await screen.findByText(/AKILI is connected to the configured Binance Spot account/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Check Binance connection/ })).toBeInTheDocument()
    expect(screen.getByText('Read-only account access')).toBeInTheDocument()
  })
})

describe('failures are shown as failures', () => {
  it('reports an unreachable backend instead of substituting an answer', async () => {
    mount({
      '/api/v1/chat': () => Promise.reject(new TypeError('Failed to fetch')),
    })

    await send('What is BTC worth?')

    const alert = await screen.findByRole('alert')
    expect(within(alert).getByText('Unable to reach AKILI')).toBeInTheDocument()
    expect(screen.queryByLabelText(/Market data for/)).not.toBeInTheDocument()
  })

  it('passes through the backend’s own 503 detail', async () => {
    mount({
      '/api/v1/chat': () => jsonResponse({ detail: 'The assistant is not configured' }, 503),
    })

    await send('Hello')

    const alert = await screen.findByRole('alert')
    expect(within(alert).getByText('AKILI is temporarily unavailable')).toBeInTheDocument()
    expect(within(alert).getByText('The assistant is not configured')).toBeInTheDocument()
  })

  it('reports a rejected model answer as a rejection, not an answer', async () => {
    mount({
      '/api/v1/chat': () =>
        jsonResponse({ detail: 'The assistant returned an unusable response' }, 502),
    })

    await send('Hello')

    const alert = await screen.findByRole('alert')
    expect(
      within(alert).getByText('AKILI could not use the assistant’s response'),
    ).toBeInTheDocument()
  })

  it('retries the exact message that failed', async () => {
    let attempt = 0
    const fetchStub = mount({
      '/api/v1/chat': () => {
        attempt += 1
        if (attempt === 1) return Promise.reject(new TypeError('Failed to fetch'))
        return jsonResponse(chatResponse())
      },
    })

    await send('What is a market order?')
    await userEvent.click(await screen.findByRole('button', { name: 'Try again' }))

    await waitFor(() => {
      expect(
        fetchStub.mock.calls.filter(([url]) => String(url).includes('/api/v1/chat')),
      ).toHaveLength(2)
      expect(JSON.parse(String(chatCall(fetchStub, 1).body)).message).toBe(
        'What is a market order?',
      )
    })
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})

describe('accessibility', () => {
  it('labels the composer, the send control, and the sidebar toggle', () => {
    mount({})

    expect(screen.getByLabelText('Message AKILI')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send message' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Show conversations' })).toHaveAttribute(
      'aria-expanded',
      'false',
    )
  })

  it('pairs every status colour with words', async () => {
    mount({})
    // The Binance chip reads its state out in text, not by colour alone.
    await waitFor(() => expect(screen.getByText('Not configured')).toBeInTheDocument())
  })

  it('announces the loading state politely', async () => {
    mount({ '/api/v1/chat': () => new Promise<Response>(() => {}) })

    await send('Hello')

    const status = await screen.findByRole('status')
    expect(status).toHaveAttribute('aria-live', 'polite')
  })
})
