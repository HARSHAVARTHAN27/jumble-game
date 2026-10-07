export type TeamName = 'Ctrl Alt Defeat' | 'Titans' | 'Vibe Tribe'
export type Phase = 'lobby' | 'countdown' | 'intro' | 'active' | 'ended' | 'answer_revealed' | 'score_revealed' | 'between' | 'completed'
export interface Team { id: string; name: TeamName; joined: number; total: number; submitted: number; members: string[]; score: number; roundGain: number; previousRank?: number }
export interface Participant { id: string; name: string; teamId: string; joinedAt?: string; isYou: boolean }
export interface Player { id: string; name: string; teamId: string; gameId: string; score: number; previousScore: number; earnedPoints?: number; waitingForGame?: boolean; hasSubmitted: boolean; answer?: string; isCorrect?: boolean; attemptCount?: number }
export interface DrawingStroke { id: string; color: string; width: number; points: [number, number][] }
export interface QuestionData { rows?: number; cols?: number; cells?: string[]; clues?: string[]; puzzle?: string; code?: string; target?: number; numbers?: number[]; image?: string; operators?: string[]; useAllNumbers?: boolean; isArtist?: boolean; secretCard?: string; cardExpiresAt?: string; artistId?: string; artists?: Record<string, string>; strokes?: DrawingStroke[]; canvases?: Record<string, DrawingStroke[]> }
export interface Question { id: string; question: string; questionType: string; gameType: string; questionData?: QuestionData; options: string[]; number: number; durationSeconds: number; startedAt?: string; correctAnswer?: string; hostAnswer?: string; isDemo?: boolean; scoredCount?: number; instructions?: string; lockAfterAttempt?: boolean; subphase?: 'prepare' | 'answer'; deadline?: string }
export interface ReviewSubmission { id: string; playerId: string; teamId: string; answer: string; correct: boolean; elapsed: number }
export interface SessionEnding { endedReason?: 'replaced'; newGameAvailable?: boolean }
export interface GameState extends SessionEnding { id: string; title: string; phase: Phase; round: number; totalRounds: number; roundId?: string; roundName: string; roundDescription: string; joined: number; total: number; submitted: number; teams: Team[]; participants?: Participant[]; question?: Question; countdownStartedAt?: string; completedAt?: string; serverTime?: string; player?: Player; isLastQuestion?: boolean; reviewSubmissions?: ReviewSubmission[] }
export interface JoinResponse { player: { id: string; name: string; waitingForGame?: boolean }; team: { id: string; name: string }; game: { id: string; status: string } }
export const TEAM_NAMES: TeamName[] = ['Ctrl Alt Defeat', 'Titans', 'Vibe Tribe']
export function teamName(name: string): TeamName {
  if (TEAM_NAMES.includes(name as TeamName)) return name as TeamName
  throw new Error('Unknown team returned by the server')
}
