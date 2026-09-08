/**
 * AKILI.
 *
 * The shell wires three real sources of state together and nothing else:
 *
 *   - `useChat`      -> POST /api/v1/chat, the only chat endpoint
 *   - `useBinanceConnection` -> the backend's own Binance availability
 *   - `useBackendHealth`     -> GET /health, so "offline" is a fact
 *
 * There is no store of seeded data anywhere behind this. The first render is an
 * empty conversation and a set of honest unavailable states; everything else
 * arrives because the user asked for it and the backend answered.
 */

import { useMemo, useState } from 'react'
import { ChatPanel } from './components/chat/ChatPanel'
import { BinanceView } from './components/layout/BinanceView'
import { ContextRail } from './components/layout/ContextRail'
import { Header } from './components/layout/Header'
import { InfoView } from './components/layout/InfoView'
import { Sidebar, type SidebarView } from './components/layout/Sidebar'
import { useBackendHealth } from './hooks/useBackendHealth'
import { useBinanceConnection } from './hooks/useBinanceConnection'
import { useChat } from './hooks/useChat'
import type { MarketDataFacts } from './types/contract'
import styles from './components/layout/layout.module.css'

export default function App() {
  const chat = useChat()
  const binance = useBinanceConnection()
  const health = useBackendHealth()

  const [view, setView] = useState<SidebarView>('chat')
  const [isSidebarOpen, setSidebarOpen] = useState(false)

  /**
   * The most recent reading of this session — the last turn that actually came
   * back with `market_data`. Null until one does; never a placeholder.
   */
  const latestReading = useMemo<MarketDataFacts | null>(() => {
    for (let index = chat.turns.length - 1; index >= 0; index -= 1) {
      const turn = chat.turns[index]
      if (turn?.kind === 'agent' && turn.marketData) return turn.marketData
    }
    return null
  }, [chat.turns])

  function changeView(next: SidebarView) {
    setView(next)
    setSidebarOpen(false)
  }

  function openChat() {
    chat.startNewConversation()
    changeView('chat')
  }

  function openConversation(id: string) {
    chat.openConversation(id)
    changeView('chat')
  }

  return (
    <div className={styles.shell}>
      <Header
        binanceState={binance.state}
        health={health}
        onSelectBinance={() => changeView('binance')}
        onToggleSidebar={() => setSidebarOpen((open) => !open)}
        isSidebarOpen={isSidebarOpen}
      />

      <div className={styles.body}>
        <Sidebar
          conversations={chat.conversations}
          activeConversationId={chat.conversationId}
          view={view}
          isOpen={isSidebarOpen}
          onNewChat={openChat}
          onOpenConversation={openConversation}
          onChangeView={changeView}
        />

        <main className={styles.main}>
          {view === 'chat' ? (
            <ChatPanel
              turns={chat.turns}
              isSending={chat.isSending}
              onSend={chat.send}
              onRetry={chat.retry}
              composerDisabled={health.status === 'down'}
              composerDisabledReason="AKILI is offline — start the backend to send a message"
            />
          ) : view === 'binance' ? (
            <BinanceView
              state={binance.state}
              metadata={binance.metadata}
              onRefresh={binance.refresh}
            />
          ) : (
            <InfoView />
          )}
        </main>

        <ContextRail
          latestReading={latestReading}
          binanceState={binance.state}
          binanceMetadata={binance.metadata}
          onRefreshBinance={binance.refresh}
        />
      </div>
    </div>
  )
}
