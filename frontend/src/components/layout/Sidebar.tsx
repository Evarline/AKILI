/**
 * The sidebar: new chat, this session's conversations, and navigation.
 *
 * The conversation list is real but narrow. The backend persists conversations
 * and indexes them for "this user's recent conversations", but it exposes no
 * route to read them — `POST /api/v1/chat` is the only conversation endpoint.
 * So the list holds the conversations this session actually created, identified
 * by the `conversation_id`s the backend returned, and it says outright that
 * earlier ones cannot be listed. It is never padded with examples.
 *
 * The reference's "Quick actions" row (Buy crypto, Portfolio) is not
 * reproduced: buying and portfolio are not things this build can do, and a
 * control that cannot act is worse than no control.
 */

import type { ConversationSummary } from '../../hooks/useChat'
import { formatRelative } from '../../lib/time'
import { Icon, type IconName } from '../ui/Icon'
import { cx } from '../ui/primitives'
import styles from './layout.module.css'
import binanceColoredIcon from '../../../Binance Icon - Colored - zonalogo.com.svg'

export type SidebarView = 'chat' | 'binance' | 'about'

const NAV: Array<{ view: SidebarView; icon: IconName | 'binance'; label: string }> = [
  { view: 'chat', icon: 'message', label: 'Conversation' },
  { view: 'binance', icon: 'binance', label: 'Binance account' },
  { view: 'about', icon: 'shield', label: 'How AKILI works' },
]

export function Sidebar({
  conversations,
  activeConversationId,
  view,
  isOpen,
  onNewChat,
  onOpenConversation,
  onChangeView,
}: {
  conversations: ConversationSummary[]
  activeConversationId: string | null
  view: SidebarView
  isOpen: boolean
  onNewChat: () => void
  onOpenConversation: (id: string) => void
  onChangeView: (view: SidebarView) => void
}) {
  return (
    <aside
      id="akili-sidebar"
      className={cx(styles.sidebar, isOpen && styles.sidebarOpen)}
      aria-label="Conversations and navigation"
    >
      <button type="button" className={styles.newChat} onClick={onNewChat}>
        <span className={styles.newChatIcon} aria-hidden>
          <Icon name="message" size={16} />
        </span>
        <span className={styles.newChatLabel}>New chat</span>
        <Icon name="plus" size={16} className={styles.newChatPlus} />
      </button>

      <nav className={styles.nav} aria-label="Sections">
        <ul className={styles.navList}>
          {NAV.map((item) => (
            <li key={item.view}>
              <button
                type="button"
                className={cx(styles.navItem, view === item.view && styles.navItemActive)}
                onClick={() => onChangeView(item.view)}
                aria-current={view === item.view ? 'page' : undefined}
              >
                {item.icon === 'binance' ? (
                  <img src={binanceColoredIcon} alt="" className={styles.navBinanceIcon} />
                ) : (
                  <Icon name={item.icon} size={16} className={styles.navIcon} />
                )}
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <div className={styles.conversations}>
        <h2 className={styles.sectionLabel}>This session</h2>

        {conversations.length === 0 ? (
          <p className={styles.emptyList}>
            No conversations yet. Send a message and it will appear here.
          </p>
        ) : (
          <ul className={styles.conversationList}>
            {conversations.map((conversation) => (
              <li key={conversation.id}>
                <button
                  type="button"
                  className={cx(
                    styles.conversationItem,
                    conversation.id === activeConversationId && styles.conversationItemActive,
                  )}
                  onClick={() => onOpenConversation(conversation.id)}
                  aria-current={conversation.id === activeConversationId ? 'true' : undefined}
                >
                  <span className={styles.conversationIcon} aria-hidden>
                    <Icon name="message" size={15} />
                  </span>
                  <span className={styles.conversationText}>
                    <span className={styles.conversationTitle}>{conversation.title}</span>
                    <span className={styles.conversationMeta}>
                      {conversation.turnCount} message{conversation.turnCount === 1 ? '' : 's'}
                    </span>
                  </span>
                  <span className={styles.conversationTime}>
                    {formatRelative(conversation.lastActivityAt)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}

        <p className={styles.listNote}>
          AKILI stores conversations, but has no endpoint to list them yet, so only this
          session&rsquo;s appear here.
        </p>
      </div>

      <div className={styles.security}>
        <p className={styles.securityTitle}>
          <Icon name="shield" size={15} className={styles.securityIcon} />
          Your security matters
        </p>
        <p className={styles.securityBody}>
          AKILI holds no Binance credentials in your browser and never calls Binance from it. Every
          market figure is read by AKILI&rsquo;s backend, and no order can be placed in this build.
        </p>
      </div>
    </aside>
  )
}
