import { API_URL, query } from './api'
import { supabase } from './supabase'
import type { Connection } from './realtimeService'
export function subscribeLive(gameId: string, playerId: string | undefined, host: boolean, onState: (data: Record<string, unknown>) => void, onStatus: (state: Connection) => void) {
  let stopped = false, socket: WebSocket | undefined, retry: ReturnType<typeof setTimeout> | undefined
  let delay = 1000
  const connect = async () => {
    if (stopped) return
    onStatus('connecting')
    const token = host ? (await supabase?.auth.getSession())?.data.session?.access_token : undefined
    if (stopped) return
    if (host && !token) { onStatus('unavailable'); return }
    socket = new WebSocket(API_URL.replace(/^http/, 'ws') + `/api/${host ? 'host' : 'player'}/live` + query({ game_id: gameId, player_id: host ? undefined : playerId }))
    socket.onopen = () => { if (host) socket?.send(JSON.stringify({ token })) }
    socket.onmessage = event => {
      try { const message = JSON.parse(event.data); if (message.success && message.data) { delay = 1000; onStatus('connected'); onState(message.data) } } catch { /* reconnect restores snapshot */ }
    }
    socket.onerror = () => onStatus('reconnecting')
    socket.onclose = () => { if (!stopped) { onStatus('reconnecting'); retry = setTimeout(() => void connect(), delay); delay = Math.min(delay * 2, 10000) } }
  }
  void connect()
  return () => { stopped = true; clearTimeout(retry); socket?.close() }
}
