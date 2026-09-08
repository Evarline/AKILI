/**
 * `POST /api/v1/chat` — AKILI's one chat endpoint.
 *
 * There is no second chat API and no way to bypass the agent: every message the
 * user sends goes through this route, which runs the UNDERSTAND turn, decides
 * for itself whether to make a read-only market-data call, and validates the
 * model's output against the agent contract before answering.
 */

import { request } from './client'
import type { ChatRequest, ChatResponse } from '../types/contract'

export const CHAT_PATH = '/api/v1/chat'

/** `ChatRequest.message` max_length in backend/app/api/chat.py. */
export const MAX_MESSAGE_LENGTH = 4000

export async function sendChatMessage(
  input: ChatRequest,
  signal?: AbortSignal,
): Promise<ChatResponse> {
  return request<ChatResponse>(CHAT_PATH, {
    method: 'POST',
    body: input,
    ...(signal ? { signal } : {}),
  })
}

/**
 * Turn a backend failure into copy for the user.
 *
 * Every branch corresponds to a status the backend actually produces (its
 * handlers are in backend/app/main.py). A failure is always shown as a failure:
 * nothing here substitutes an answer, a price, or a plan for an error.
 */
export function describeChatFailure(error: unknown): { title: string; detail: string } {
  if (error instanceof Error && error.name === 'NetworkError') {
    return {
      title: 'Unable to reach AKILI',
      detail: 'Check that the AKILI backend is running, then try again.',
    }
  }

  if (error instanceof Error && error.name === 'ApiError') {
    const { status } = error as Error & { status: number }
    switch (status) {
      case 400:
        return {
          title: 'AKILI could not look up that market',
          detail: 'That market is not one AKILI can read. Try naming a different asset.',
        }
      case 401:
        return {
          title: 'AKILI has no identity configured',
          detail:
            'The backend answered "not authenticated". AKILI has no login yet — set AUTH_MODE=development_fixed_user in the root .env and seed the user, then reload.',
        }
      case 404:
        return {
          title: 'That conversation is no longer available',
          detail: 'Start a new chat to continue.',
        }
      case 422:
        return {
          title: 'AKILI rejected that message',
          detail: `Messages must not be blank and must be at most ${MAX_MESSAGE_LENGTH} characters.`,
        }
      case 502:
        return {
          title: 'AKILI could not use the assistant’s response',
          detail:
            'The answer failed AKILI’s safety contract, so it was rejected rather than repaired. Try asking again.',
        }
      case 503:
        return {
          title: 'AKILI is temporarily unavailable',
          // The backend's own detail distinguishes the three 503 causes
          // (assistant not configured, market data down, database down).
          detail: (error as Error & { detail: string | null }).detail ?? 'Please try again shortly.',
        }
      default:
        return {
          title: 'AKILI could not complete that request',
          detail:
            (error as Error & { detail: string | null }).detail ?? 'Please try again shortly.',
        }
    }
  }

  return {
    title: 'AKILI could not complete that request',
    detail: 'Something unexpected went wrong. Please try again.',
  }
}
