/**
 * The centre column: the conversation and the composer.
 *
 * The transcript is exactly the turns that happened — a user's message, a
 * backend response, or a failure — in order. When there are none, the empty
 * state shows instead; the list is never pre-filled to make the interface look
 * populated.
 */

import { useEffect, useRef } from 'react'
import type { Turn } from '../../hooks/useChat'
import { AgentMessage } from './AgentMessage'
import { ChatComposer } from './ChatComposer'
import { EmptyState } from './EmptyState'
import { ErrorMessage } from './ErrorMessage'
import { ThinkingIndicator } from './ThinkingIndicator'
import { UserMessage } from './UserMessage'
import styles from './chat.module.css'

export function ChatPanel({
  turns,
  isSending,
  onSend,
  onRetry,
  composerDisabled = false,
  composerDisabledReason,
}: {
  turns: Turn[]
  isSending: boolean
  onSend: (message: string) => void
  onRetry: (turnId: string) => void
  composerDisabled?: boolean
  composerDisabledReason?: string
}) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Only once there is a transcript to follow. Scrolling to the end of an
    // empty conversation would push the welcome out of view.
    if (turns.length === 0) return
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [turns.length, isSending])

  return (
    <div className={styles.panel}>
      <div className={styles.scroll}>
        <div className={styles.transcript}>
          {turns.length === 0 && !isSending ? (
            <EmptyState />
          ) : (
            <div
              className={styles.messages}
              // Announce new turns as they arrive, without re-reading the whole
              // transcript each time.
              aria-live="polite"
              aria-relevant="additions"
            >
              {turns.map((turn) => {
                switch (turn.kind) {
                  case 'user':
                    return <UserMessage key={turn.id} turn={turn} />
                  case 'agent':
                    return <AgentMessage key={turn.id} turn={turn} />
                  case 'error':
                    return <ErrorMessage key={turn.id} turn={turn} onRetry={onRetry} />
                }
              })}
              {isSending ? <ThinkingIndicator /> : null}
            </div>
          )}
          <div ref={endRef} />
        </div>
      </div>

      <div className={styles.composerDock}>
        <div className={styles.composerInner}>
          <ChatComposer
            onSend={onSend}
            isSending={isSending}
            disabled={composerDisabled}
            {...(composerDisabledReason ? { disabledReason: composerDisabledReason } : {})}
          />
        </div>
      </div>
    </div>
  )
}
