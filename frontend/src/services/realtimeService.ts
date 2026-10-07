import { supabase } from './supabase'
import { API_URL, DEMO } from './api'
export type Connection = 'connecting' | 'connected' | 'reconnecting' | 'unavailable'
export const GAME_EVENTS = ['PLAYER_JOINED', 'PLAYER_RECONNECTED', 'GAME_STARTED', 'ROUND_STARTED', 'QUESTION_STARTED', 'QUESTION_ENDED', 'ANSWER_REVEALED', 'SUBMISSION_COUNT_UPDATED', 'SCORE_REVEALED', 'LEADERBOARD_UPDATED', 'ROUND_COMPLETED', 'GAME_COMPLETED'] as const
export type GameEvent = { event: string; payload?: Record<string, unknown> }
// Broadcast invalidates snapshots; all data and mutations still use FastAPI.
export function subscribeToGame(gameId: string, onEvent: (event: GameEvent) => void, onStatus: (status: Connection) => void) {
  onStatus('connecting')
  if (DEMO) {
    const source = new EventSource(`${API_URL}/api/events?game_id=${encodeURIComponent(gameId)}`)
    source.onopen = () => { onStatus('connected'); onEvent({ event: 'PLAYER_RECONNECTED' }) }
    source.onmessage = event => { try { onEvent(JSON.parse(event.data)) } catch { /* ignore malformed events */ } }
    source.onerror = () => onStatus('reconnecting')
    return () => source.close()
  }
  if (!supabase) { onStatus('unavailable'); return () => {} }
  const channel = supabase.channel(`game:${gameId}`)
    .on('broadcast', { event: '*' }, message => {
      if (GAME_EVENTS.includes(message.event as typeof GAME_EVENTS[number])) onEvent({ event: message.event, payload: message.payload })
    }).subscribe(status => {
      onStatus(status === 'SUBSCRIBED' ? 'connected' : status === 'CHANNEL_ERROR' || status === 'TIMED_OUT' || status === 'CLOSED' ? 'reconnecting' : 'connecting')
      if (status === 'SUBSCRIBED') onEvent({ event: 'PLAYER_RECONNECTED' })
    })
  return () => { void supabase?.removeChannel(channel) }
}
