import { request, query } from './api'
import type { GameState, Team } from '../types/game'
export const gameService = {
  getActiveGame: () => request<{ id: string; title: string; status: string }>('/api/game/active'),
  getLeaderboard: (gameId: string) => request<Team[]>('/api/game/leaderboard' + query({ game_id: gameId })),
  getState: (gameId: string) => request<GameState>('/api/game/state' + query({ game_id: gameId })),
}
