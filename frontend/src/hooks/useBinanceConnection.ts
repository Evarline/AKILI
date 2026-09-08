/**
 * Whether AKILI can start a Binance authorization right now.
 *
 * The state comes from the backend's safe signed account check, so it is never
 * inferred from local configuration or a frontend-held credential.
 */

import { useCallback, useEffect, useState } from 'react'
import {
  fetchBinanceAvailability,
  type BinanceConnectionState,
  type ClientMetadata,
} from '../api/binance'

export type BinanceConnection = {
  state: BinanceConnectionState
  metadata: ClientMetadata | null
  refresh: () => void
}

export function useBinanceConnection(): BinanceConnection {
  const [state, setState] = useState<BinanceConnectionState>('checking')
  const [metadata, setMetadata] = useState<ClientMetadata | null>(null)
  const [reloadToken, setReloadToken] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setState('checking')

    void fetchBinanceAvailability(controller.signal)
      .then((availability) => {
        if (controller.signal.aborted) return
        setState(availability.state)
        setMetadata(availability.metadata)
      })
      .catch(() => {
        if (!controller.signal.aborted) setState('unreachable')
      })

    return () => controller.abort()
  }, [reloadToken])

  const refresh = useCallback(() => setReloadToken((token) => token + 1), [])

  return { state, metadata, refresh }
}
