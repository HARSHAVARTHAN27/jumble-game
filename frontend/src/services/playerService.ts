import { post, query, request } from './api'
import type { GameState, JoinResponse } from '../types/game'
export const playerService = {
  joinGame: (name: string, employeeCode?: string) => post<JoinResponse>('/api/player/join', { name, ...(employeeCode ? { employeeCode } : {}) }),
  getPlayerState: (playerId: string, gameId: string) => request<GameState | Record<string, unknown>>('/api/player/state' + query({ player_id: playerId, game_id: gameId })),
  getCurrentQuestion: (gameId: string) => request<Record<string, unknown>>('/api/player/question/current' + query({ game_id: gameId })),
  submitAnswer: (questionId: string, answer: string, playerId: string, gameId: string, requestId: string) => post<{ answerLocked: boolean }>('/api/player/question/' + encodeURIComponent(questionId) + '/submit' + query({ player_id: playerId, game_id: gameId }), { answer, requestId }),
}
