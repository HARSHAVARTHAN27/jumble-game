import { teamName, TEAM_NAMES } from '../types/game'
import type { GameState, Phase, Player, Team } from '../types/game'
type Raw = Record<string, any>
export function emptyGame(id = ''): GameState {
  return { id, title: 'Jumble', phase: 'lobby', round: 0, totalRounds: 6, roundName: 'Awaiting round content', roundDescription: 'Round details will be provided by the host.', joined: 0, total: 0, submitted: 0, teams: TEAM_NAMES.map((name) => ({ id: name, name, joined: 0, total: 0, submitted: 0, members: [], score: 0, roundGain: 0 })) }
}
export function normalizeState(raw: Raw, previous: GameState): GameState {
  const incomingId = raw.id ?? raw.game_id
  if (incomingId && incomingId !== previous.id) previous = emptyGame(incomingId)
  const phase: Phase = raw.phase ?? ({ playing: 'intro', paused: 'between', completed: 'completed', lobby: 'lobby' } as Record<string, Phase>)[raw.status] ?? previous.phase
  const revealed = phase === 'score_revealed' || phase === 'between' || phase === 'completed' || phase === 'lobby'
  const teams: Team[] = Array.isArray(raw.teams) ? raw.teams.map((t: Raw) => {
    const name = teamName(t.name ?? t.teamName)
    const old = previous.teams.find(team => team.name === name)
    return { id: t.id ?? old?.id ?? name, name, joined: t.joined ?? old?.joined ?? 0, total: t.total ?? old?.total ?? 0, submitted: t.submitted ?? 0, members: t.members ?? [], score: revealed ? (t.score ?? old?.score ?? 0) : old?.score ?? 0, roundGain: revealed ? (t.roundGain ?? 0) : 0, previousRank: t.previousRank }
  }) : previous.teams
  const q = raw.question
  const question = q && typeof q === 'object' ? { id: q.id, question: q.question ?? q.question_text, questionType: q.questionType ?? q.question_type ?? 'mcq', gameType: q.gameType ?? q.game_type ?? 'mcq', questionData: q.questionData ?? q.question_data, options: q.options ?? q.question_data?.options ?? [], number: q.number ?? q.question_number ?? 1, durationSeconds: q.durationSeconds ?? q.duration_seconds ?? 30, startedAt: q.startedAt ?? q.started_at, hostAnswer: q.hostAnswer, isDemo: q.isDemo, scoredCount: q.scoredCount, instructions: q.instructions, lockAfterAttempt: q.lockAfterAttempt, subphase: q.subphase, deadline: q.deadline, correctAnswer: ['answer_revealed', 'score_revealed', 'between', 'completed'].includes(phase) ? q.correctAnswer ?? q.correct_answer : undefined } : raw.phase && !q ? undefined : previous.question
  let player = previous.player
  if (raw.player) {
    const p = raw.player
    player = { ...player, ...p, teamId: p.teamId ?? p.team_id ?? player?.teamId, gameId: p.gameId ?? raw.game_id ?? player?.gameId, hasSubmitted: p.hasSubmitted ?? raw.submission_status?.has_submitted ?? raw.answer_locked ?? false, score: revealed ? (p.score ?? raw.individual_score?.committed_score ?? player?.score ?? 0) : player?.score ?? 0, previousScore: p.previousScore ?? player?.score ?? 0, earnedPoints: revealed ? p.earnedPoints : undefined, isCorrect: ['answer_revealed', 'score_revealed', 'completed'].includes(phase) ? p.isCorrect : undefined } as Player
  }
  return { ...previous, endedReason: raw.endedReason ?? undefined, newGameAvailable: Boolean(raw.newGameAvailable), id: raw.id ?? raw.game_id ?? previous.id, title: raw.title ?? previous.title, phase, round: raw.round ?? raw.current_round ?? previous.round, totalRounds: raw.totalRounds ?? 6, roundId: raw.roundId ?? raw.round_id ?? previous.roundId, roundName: raw.roundName ?? previous.roundName, roundDescription: raw.roundDescription ?? previous.roundDescription, joined: raw.joined ?? previous.joined, total: raw.total ?? previous.total, submitted: raw.submitted ?? previous.submitted, countdownStartedAt: raw.countdownStartedAt, completedAt: raw.completedAt ?? previous.completedAt, serverTime: raw.serverTime, participants: raw.participants ?? previous.participants ?? [], isLastQuestion: raw.isLastQuestion, reviewSubmissions: raw.reviewSubmissions ?? [], teams, question, player }
}

