export const ROUND_TYPES = ['memory', 'emoji', 'connection', 'target', 'drawing', 'technical'] as const
export type RoundType = typeof ROUND_TYPES[number]
export const ROUND_NAMES = ['Memory Grid', 'Emoji Decode', 'Connection Hunt', 'Target Drop', 'Draw & Guess', 'Technical Showdown']
export const ROUND_RULES = [
  '10 seconds to memorize, then 30 seconds to answer. Correct: 20 marks; within 5 seconds: +5.',
  '30 seconds to decode. Correct: 20 marks; first correct team: +10.',
  'Four clues at 0, 7, 14 and 21 seconds. Correct: 40 / 30 / 20 / 10 marks.',
  '30 seconds. Exact: 40; distance 1: 30; distance 2–3: 20; distance 4–5: 10. Use each number at most once.',
  '10 seconds for the private card, then 30 seconds to draw and guess. Correct within 15 seconds: 30; within 30: 20. Host sees the card.',
  '30 seconds. Correct: 30 marks; first correct team: +10. Optional final hard question: 50 base marks.',
]
export interface ContentQuestion { id: string; prompt: string; answerType: 'mcq' | 'text' | 'output' | 'expression'; options: string[]; acceptedAnswers: string[]; data: { rows?: number; cols?: number; cells?: string[]; puzzle?: string; clues?: string[]; target?: number; numbers?: number[]; code?: string; image?: string; operators?: string[]; useAllNumbers?: boolean; exampleSolution?: string }; hard: boolean; isDemo?: boolean; memoryTime?: number; answerTime?: number; instructions?: string; scoringRule?: 'existing' | 'bank-v2'; lockAfterAttempt?: boolean }
export interface ContentRound { gameType: RoundType; questions: ContentQuestion[] }
export interface ContentError { path: string; message: string }
export interface GameContent { version: number; rounds: ContentRound[] }
export const blankContent = (): GameContent => ({ version: 0, rounds: ROUND_TYPES.map(gameType => ({ gameType, questions: [] })) })
export const blankQuestion = (kind: RoundType): ContentQuestion => ({ id: crypto.randomUUID(), prompt: '', answerType: kind === 'target' ? 'expression' : kind === 'memory' || kind === 'technical' ? 'mcq' : 'text', options: kind === 'memory' || kind === 'technical' ? ['', '', '', ''] : [], acceptedAnswers: [], hard: false, data: kind === 'memory' ? { rows: 3, cols: 3, cells: Array(9).fill('') } : kind === 'connection' ? { clues: ['', '', '', ''] } : kind === 'target' ? { target: 50, numbers: [8, 6, 4, 3] } : kind === 'emoji' ? { puzzle: '' } : {} })
