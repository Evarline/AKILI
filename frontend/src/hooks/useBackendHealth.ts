/**
 * Reachability of the AKILI backend, so failure copy can be accurate about
 * whether AKILI is down or AKILI said no.
 */

import { useEffect, useState } from 'react'
import { fetchHealth } from '../api/health'

export type BackendHealth = {
  status: 'checking' | 'up' | 'down'
  version: string | null
}

export function useBackendHealth(): BackendHealth {
  const [health, setHealth] = useState<BackendHealth>({ status: 'checking', version: null })

  useEffect(() => {
    const controller = new AbortController()

    void fetchHealth(controller.signal).then((result) => {
      if (controller.signal.aborted) return
      setHealth(
        result.reachable
          ? { status: 'up', version: result.version || null }
          : { status: 'down', version: null },
      )
    })

    return () => controller.abort()
  }, [])

  return health
}
