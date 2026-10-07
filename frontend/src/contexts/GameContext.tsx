import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import type { GameState, JoinResponse, Player } from '../types/game'
import { teamName } from '../types/game'
import { emptyGame, normalizeState } from '../services/normalize'
import { ApiError } from '../services/api'
import { gameService } from '../services/gameService'
import { playerService } from '../services/playerService'
import { hostService } from '../services/hostService'
import { subscribeToGame } from '../services/realtimeService'
import { subscribeLive } from '../services/liveService'
import { DEMO } from '../services/api'
import type { Connection } from '../services/realtimeService'
interface Context { state: GameState; loading: boolean; error: string; connection: Connection; clockOffset: number; refresh: () => Promise<void>; join: (name: string, code?: string) => Promise<JoinResponse>; submit: (answer: string) => Promise<void>; hostAction: (action: HostAction) => Promise<void>; clearError: () => void }
export type HostAction = 'create' | 'start' | 'round' | 'question' | 'end' | 'answer' | 'scores' | 'next' | 'complete' | 'finish' | 'replay'
const GameContext = createContext<Context | null>(null)
const sessionKey = 'jumble.player'
function storedPlayer(): Player | undefined {
  try { const value = JSON.parse(localStorage.getItem(sessionKey) || 'null'); return value?.id && (value?.gameId || value?.waitingForGame) ? value : undefined } catch { return undefined }
}
function cachedTeams(gameId: string) {
  try { const cache = JSON.parse(localStorage.getItem('jumble.visible-teams') || 'null'); return cache?.gameId === gameId && Array.isArray(cache.teams) ? cache.teams : undefined } catch { return undefined }
}
export function GameProvider({ children }: { children: ReactNode }) {
  const host = useLocation().pathname.startsWith('/control')
  const [state, setState] = useState<GameState>(() => { const player = storedPlayer(); const id = player?.gameId || localStorage.getItem('jumble.game') || ''; const base = emptyGame(id); return { ...base, teams: cachedTeams(id) ?? base.teams, player } })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [connection, setConnection] = useState<Connection>('connecting')
  const [clockOffset, setClockOffset] = useState(0)
  const current = useRef(state); current.current = state
  const epoch = useRef(0)
  const actionPending = useRef(false)
  const mounted = useRef(true)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  useEffect(() => { if (state.id) localStorage.setItem('jumble.visible-teams', JSON.stringify({ gameId: state.id, teams: state.teams })) }, [state.id, state.teams])
  const apply = useCallback((raw: Record<string, unknown>) => {
    if (raw.serverTime) setClockOffset(Date.parse(String(raw.serverTime)) - Date.now())
    setState(old => {
      const next = normalizeState(raw, old)
      if (next.id) localStorage.setItem('jumble.game', next.id)
      if (next.player) localStorage.setItem(sessionKey, JSON.stringify(next.player))
      return next
    })
  }, [])
  const refresh = useCallback(async (afterAction = false) => {
    if (actionPending.current && !afterAction) return
    const sequence = ++epoch.current
    try {
      const old = current.current
      if (!host && !old.player) return
      let raw: Record<string, unknown>
      if (!host && old.player) raw = await playerService.getPlayerState(old.player.id, old.player.gameId) as unknown as Record<string, unknown>
      else {
        let active: { id: string }
        try { active = await gameService.getActiveGame() }
        catch (e) { if (host && old.id && e instanceof ApiError && e.code === 'NO_ACTIVE_GAME') active = { id: old.id }; else throw e }
        if (host) {
          try { raw = await hostService.getQuestionStatus(active.id) as unknown as Record<string, unknown> }
          catch (e) { if (!(e instanceof ApiError) || e.code !== 'ENDPOINT_UNAVAILABLE') throw e; raw = { ...await hostService.getHostLobby(active.id), id: active.id } }
        } else raw = await gameService.getState(active.id) as unknown as Record<string, unknown>
      }
      if (mounted.current && sequence === epoch.current) { apply(raw); setError('') }
    } catch (e) {
      if (mounted.current && sequence === epoch.current && e instanceof ApiError && e.code === 'NO_ACTIVE_GAME') {
        setState(emptyGame()); localStorage.removeItem('jumble.game'); setError('')
      }
      if (mounted.current && sequence === epoch.current && !(e instanceof ApiError && e.code === 'NO_ACTIVE_GAME')) setError(e instanceof Error ? e.message : 'Unable to restore the game.')
    } finally { if (mounted.current && sequence === epoch.current) setLoading(false) }
  }, [host, apply])
  useEffect(() => { setLoading(true); void refresh() }, [refresh])
  // Foundation fallback while private broadcast publication is being completed.
  useEffect(() => {
    if (!state.id && !state.player?.waitingForGame) return
    const timer = window.setInterval(() => { if (!actionPending.current) void refresh() }, state.phase === 'lobby' ? 5000 : 2000)
    return () => window.clearInterval(timer)
  }, [state.id, state.phase, state.player?.waitingForGame, refresh])
  useEffect(() => {
    if (!state.id) { setConnection('unavailable'); return }
    let active = true
    let scheduled: ReturnType<typeof setTimeout> | undefined
    const unsubscribe = !DEMO ? subscribeLive(state.id, state.player?.id, host, raw => {
      if (active && current.current.id === state.id && raw.id === state.id && !actionPending.current && mounted.current) apply(raw)
    }, setConnection) : subscribeToGame(state.id, () => {
      if (scheduled) clearTimeout(scheduled)
      scheduled = setTimeout(() => { void refresh() }, 70)
    }, setConnection)
    const onFocus = () => { void refresh() }
    const onOffline = () => setConnection('reconnecting')
    window.addEventListener('online', onFocus); window.addEventListener('focus', onFocus); window.addEventListener('offline', onOffline)
    return () => { active = false; unsubscribe(); clearTimeout(scheduled); window.removeEventListener('online', onFocus); window.removeEventListener('focus', onFocus); window.removeEventListener('offline', onOffline) }
  }, [state.id, state.player?.id, host, refresh, apply])
  const join = async (name: string, code?: string) => {
    if (actionPending.current) throw new ApiError('GAME_BUSY', 'Please wait for the current action to finish.')
    actionPending.current = true
    try {
    ++epoch.current
    const response = await playerService.joinGame(name, code)
    const player: Player = { id: response.player.id, name: response.player.name, teamId: response.team.id, gameId: response.game.id, waitingForGame: response.player.waitingForGame ?? false, score: 0, previousScore: 0, hasSubmitted: false }
    localStorage.setItem(sessionKey, JSON.stringify(player)); localStorage.setItem('jumble.game', response.game.id)
    const assignedName = teamName(response.team.name)
    ++epoch.current
    const next = emptyGame(response.game.id)
    next.teams = next.teams.map(t => t.name === assignedName ? { ...t, id: response.team.id } : t)
    next.player = player
    current.current = next; setState(next)
    setError('')
    // Fetch counts/team IDs immediately instead of waiting for a broadcast.
    try { apply(await playerService.getPlayerState(player.id, player.gameId) as Record<string, unknown>) } catch { /* lobby refresh will retry */ }
    return response
    } finally { actionPending.current = false }
  }
  const submit = async (answer: string) => {
    const s = current.current
    if (actionPending.current || !s.player || !s.question || s.player.hasSubmitted || s.phase !== 'active') return
    actionPending.current = true
    try {
      const result = await playerService.submitAnswer(s.question.id, answer, s.player.id, s.id, crypto.randomUUID())
      setState(old => ({ ...old, player: old.player ? { ...old.player, hasSubmitted: result.answerLocked, answer } : undefined }))
      await refresh(true)
    } catch (e) {
      if (e instanceof ApiError && e.code === 'ANSWER_ALREADY_SUBMITTED') { setState(old => ({ ...old, player: old.player ? { ...old.player, hasSubmitted: true } : undefined })); await refresh(true) }
      else throw e
    } finally { actionPending.current = false }
  }
  const hostAction = async (action: HostAction) => {
    if (actionPending.current) return
    actionPending.current = true
    ++epoch.current
    const s = current.current
    try {
      if (action === 'create') {
        const created = await hostService.createGame()
        ++epoch.current
        const next = emptyGame(created.id); current.current = next; setState(next); localStorage.setItem('jumble.game', created.id)
        localStorage.removeItem('jumble.visible-teams'); setError('')
      } else {
        const q = s.question?.id; const r = s.roundId
        const actions: Record<HostAction, () => Promise<unknown>> = {
          create: () => Promise.resolve(), start: () => hostService.startGame(s.id), round: () => r ? hostService.startRound(s.id, r) : Promise.reject(new ApiError('QUESTION_NOT_ACTIVE')),
          question: () => q ? hostService.startQuestion(s.id, q) : Promise.reject(new ApiError('QUESTION_NOT_ACTIVE')),
          end: () => q ? hostService.endQuestion(s.id, q) : Promise.reject(new ApiError('QUESTION_NOT_ACTIVE')),
          answer: () => q ? hostService.revealAnswer(s.id, q) : Promise.reject(new ApiError('QUESTION_NOT_ACTIVE')),
          scores: () => q ? hostService.revealScores(s.id, q) : Promise.reject(new ApiError('QUESTION_NOT_ACTIVE')),
          next: () => hostService.nextQuestion(s.id), complete: () => r ? hostService.completeRound(s.id, r) : Promise.reject(new ApiError('QUESTION_NOT_ACTIVE')),
          finish: () => hostService.finishGame(s.id), replay: async () => { const created = await hostService.replay(s.id); const next = emptyGame(created.id); current.current = next; setState(next); localStorage.setItem('jumble.game', created.id) },
        }
        await actions[action]()
      }
      await refresh(true)
    } finally { actionPending.current = false }
  }
  return <GameContext.Provider value={{ state, loading, error, connection, clockOffset, refresh, join, submit, hostAction, clearError: () => setError('') }}>{children}</GameContext.Provider>
}
export function useGame() { const value = useContext(GameContext); if (!value) throw new Error('GameProvider is missing'); return value }
