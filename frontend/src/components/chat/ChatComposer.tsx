/**
 * The composer.
 *
 * The user always initiates. Enter sends, Shift+Enter adds a line, and the
 * textarea grows with its content. The character limit is the backend's own
 * (`ChatRequest.message`, max_length 4000), so the client refuses what the
 * backend would reject with a 422 rather than sending it and reporting a
 * failure the user could have avoided.
 */

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { MAX_MESSAGE_LENGTH } from '../../api/chat'
import { Icon } from '../ui/Icon'
import { cx } from '../ui/primitives'
import styles from './chat.module.css'

const MAX_ROWS_HEIGHT = 168

export function ChatComposer({
  onSend,
  isSending,
  disabled = false,
  disabledReason,
}: {
  onSend: (message: string) => void
  isSending: boolean
  disabled?: boolean
  disabledReason?: string
}) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Grow to fit, up to a cap, then scroll.
  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_ROWS_HEIGHT)}px`
  }, [value])

  const trimmed = value.trim()
  const isOverLimit = value.length > MAX_MESSAGE_LENGTH
  const canSend = trimmed.length > 0 && !isOverLimit && !isSending && !disabled

  function submit(event?: FormEvent) {
    event?.preventDefault()
    if (!canSend) return
    onSend(trimmed)
    setValue('')
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  const remaining = MAX_MESSAGE_LENGTH - value.length
  const showCounter = value.length > MAX_MESSAGE_LENGTH - 400

  return (
    <form className={styles.composer} onSubmit={submit}>
      <div className={cx(styles.composerShell, isOverLimit && styles.composerShellInvalid)}>
        <label htmlFor="akili-composer" className="visually-hidden">
          Message AKILI
        </label>
        <textarea
          id="akili-composer"
          ref={textareaRef}
          className={styles.textarea}
          rows={1}
          value={value}
          placeholder={disabled ? (disabledReason ?? 'AKILI is unavailable') : 'Type your message…'}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          aria-describedby="akili-composer-help"
          aria-invalid={isOverLimit}
        />
        <button
          type="submit"
          className={styles.sendButton}
          disabled={!canSend}
          aria-label={isSending ? 'AKILI is answering' : 'Send message'}
        >
          <Icon name="send" size={17} />
        </button>
      </div>

      <p id="akili-composer-help" className={styles.composerHelp}>
        {isOverLimit ? (
          <span className={styles.composerError}>
            {value.length - MAX_MESSAGE_LENGTH} characters over the {MAX_MESSAGE_LENGTH}-character
            limit.
          </span>
        ) : showCounter ? (
          <span className="tabular">{remaining} characters left</span>
        ) : (
          <span>
            AKILI explains, reads market data, and plans. It never places an order.
            <span className={styles.hintKeys}> Enter to send, Shift+Enter for a new line.</span>
          </span>
        )}
      </p>
    </form>
  )
}
