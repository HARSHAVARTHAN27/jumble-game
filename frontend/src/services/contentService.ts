import { request, post, query } from './api'
import type { GameContent, ContentError } from '../types/content'
export const contentService = {
  bank: (gameId: string) => request<GameContent>('/api/host/game/content/bank' + query({ game_id: gameId })),
  clue: (gameId: string) => post('/api/host/game/clue' + query({ game_id: gameId })),
  get: (gameId: string) => request<GameContent>('/api/host/game/content' + query({ game_id: gameId })),
  save: (gameId: string, content: GameContent) => request<GameContent & { errors: ContentError[] }>('/api/host/game/content' + query({ game_id: gameId }), { method: 'PUT', body: JSON.stringify(content) }),
  validate: (gameId: string) => request<{ ready: boolean; errors: ContentError[] }>('/api/host/game/content/validate' + query({ game_id: gameId })),
  upload: (gameId: string, file: File) => { const data = new FormData(); data.append('file', file); return request<{ cell: string; url: string }>('/api/host/game/content/image' + query({ game_id: gameId }), { method: 'POST', body: data }) },
  image: (gameId: string, path: string) => request<{ url: string }>('/api/host/game/content/image' + query({ game_id: gameId, path })),
  review: (gameId: string, submissionId: string, correct: boolean) => post('/api/host/game/review/' + encodeURIComponent(submissionId) + query({ game_id: gameId }), { correct }),
  reassign: (gameId: string, teamId: string, playerId: string) => post('/api/host/game/artist' + query({ game_id: gameId }), { teamId, playerId }),
}
