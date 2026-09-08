/**
 * AKILI's conversation state.
 *
 * Every turn in `messages` came from a real exchange with `POST /api/v1/chat`:
 * the user's own text, or a response the backend returned. There is no seed
 * data, no example conversation, and no placeholder turn — a fresh session
 * starts empty and is populated only by real interaction.
 *
 * The backend has no conversation-listing endpoint, so the sidebar's list is
 * built from the `conversation_id`s this session actually created. Those ids are
 * real; the list simply cannot include conversations from earlier sessions, and
 * the UI says so rather than inventing entries.
 */

import { useCallback, useMemo, useRef, useState } from 'react'
import { describeChatFailure, sendChatMessage } from '../api/chat'
import type { ChatResponse, Interpretation, MarketDataFacts } from '../types/contract'

export type UserTurn = {
  kind: 'user'
  id: string
  /** USER INPUT: exactly what the user typed. */
  text: string
  /** Client-side only — the backend does not return message timestamps. */
  sentAt: number
}

export type AgentTurn = {
  kind: 'agent'
  id: string
  /** MODEL INTERPRETATION, validated by the backend against the agent contract. */
  interpretation: Interpretation
  /** BINANCE FACT, present only when the turn fetched market data. */
  marketData: MarketDataFacts | null
  agentRunId: string
  receivedAt: number
}

export type FailedTurn = {
  kind: 'error'
  id: string
  title: string
  detail: string
  /** The message that failed, so the user can retry it verbatim. */
  attemptedMessage: string
  occurredAt: number
}

export type Turn = UserTurn | AgentTurn | FailedTurn

export type ConversationSummary = {
  id: string
  /** The conversation's first user message — real text, used as its title. */
  title: string
  turnCount: number
  lastActivityAt: number
}

export type ChatState = {
  turns: Turn[]
  conversationId: string | null
  isSending: boolean
  conversations: ConversationSummary[]
}

let sequence = 0
function nextId(prefix: string): string {
  sequence += 1
  return `${prefix}-${sequence}`
}

type Session = {
  conversationId: string | null
  turns: Turn[]
}

export function useChat() {
  const [session, setSession] = useState<Session>({ conversationId: null, turns: [] })
  const [isSending, setIsSending] = useState(false)
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  /** Conversations this session has loaded, so switching back keeps real turns. */
  const archive = useRef(new Map<string, Turn[]>())
  const inFlight = useRef<AbortController | null>(null)

  const rememberConversation = useCallback((id: string, turns: Turn[]) => {
    archive.current.set(id, turns)

    const firstUserTurn = turns.find((turn): turn is UserTurn => turn.kind === 'user')
    const lastTurn = turns[turns.length - 1]
    setConversations((current) => {
      const summary: ConversationSummary = {
        id,
        title: firstUserTurn?.text ?? 'Untitled conversation',
        turnCount: turns.filter((turn) => turn.kind === 'user').length,
        lastActivityAt:
          lastTurn === undefined
            ? Date.now()
            : lastTurn.kind === 'user'
              ? lastTurn.sentAt
              : lastTurn.kind === 'agent'
                ? lastTurn.receivedAt
                : lastTurn.occurredAt,
      }
      const without = current.filter((entry) => entry.id !== id)
      return [summary, ...without]
    })
  }, [])

  const send = useCallback(
    async (message: string) => {
      const text = message.trim()
      if (!text || isSending) return

      inFlight.current?.abort()
      const controller = new AbortController()
      inFlight.current = controller

      const userTurn: UserTurn = {
        kind: 'user',
        id: nextId('user'),
        text,
        sentAt: Date.now(),
      }
      // The user's own turn appears immediately; nothing is shown for AKILI's
      // side until the backend has actually answered.
      setSession((current) => ({ ...current, turns: [...current.turns, userTurn] }))
      setIsSending(true)

      try {
        const conversationId = session.conversationId
        const result: ChatResponse = await sendChatMessage(
          {
            message: text,
            ...(conversationId ? { conversation_id: conversationId } : {}),
          },
          controller.signal,
        )

        const agentTurn: AgentTurn = {
          kind: 'agent',
          id: nextId('agent'),
          interpretation: result.response,
          marketData: result.market_data,
          agentRunId: result.agent_run_id,
          receivedAt: Date.now(),
        }

        setSession((current) => {
          const turns = [...current.turns, agentTurn]
          rememberConversation(result.conversation_id, turns)
          return { conversationId: result.conversation_id, turns }
        })
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') return

        const { title, detail } = describeChatFailure(error)
        const failure: FailedTurn = {
          kind: 'error',
          id: nextId('error'),
          title,
          detail,
          attemptedMessage: text,
          occurredAt: Date.now(),
        }
        setSession((current) => ({ ...current, turns: [...current.turns, failure] }))
      } finally {
        if (inFlight.current === controller) inFlight.current = null
        setIsSending(false)
      }
    },
    [isSending, rememberConversation, session.conversationId],
  )

  const startNewConversation = useCallback(() => {
    inFlight.current?.abort()
    inFlight.current = null
    setIsSending(false)
    setSession({ conversationId: null, turns: [] })
  }, [])

  /** Reopen a conversation this session created. Its turns are the real ones. */
  const openConversation = useCallback((id: string) => {
    const turns = archive.current.get(id)
    if (!turns) return
    inFlight.current?.abort()
    inFlight.current = null
    setIsSending(false)
    setSession({ conversationId: id, turns })
  }, [])

  /** Drop a failed turn and resend the message it was carrying. */
  const retry = useCallback(
    (turnId: string) => {
      const failure = session.turns.find(
        (turn): turn is FailedTurn => turn.kind === 'error' && turn.id === turnId,
      )
      if (!failure) return
      setSession((current) => ({
        ...current,
        // Remove the failed turn and the user turn it was the answer to; `send`
        // re-adds the user turn, so the message is not duplicated.
        turns: current.turns.filter(
          (turn) =>
            turn.id !== turnId &&
            !(turn.kind === 'user' && turn.text === failure.attemptedMessage && isLastUser(current.turns, turn)),
        ),
      }))
      void send(failure.attemptedMessage)
    },
    [send, session.turns],
  )

  const state = useMemo<ChatState>(
    () => ({
      turns: session.turns,
      conversationId: session.conversationId,
      isSending,
      conversations,
    }),
    [conversations, isSending, session.conversationId, session.turns],
  )

  return { ...state, send, startNewConversation, openConversation, retry }
}

function isLastUser(turns: Turn[], candidate: UserTurn): boolean {
  const userTurns = turns.filter((turn): turn is UserTurn => turn.kind === 'user')
  return userTurns[userTurns.length - 1]?.id === candidate.id
}
