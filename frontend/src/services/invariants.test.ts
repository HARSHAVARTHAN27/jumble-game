import { describe, expect, it } from 'vitest'
import { emptyGame, normalizeState } from './normalize'
import { remainingSeconds } from '../hooks/useCountdown'
describe('server visibility boundaries', () => {
  it('resets old scores, questions, and player state when the game ID changes', () => {
    const old = normalizeState({ id: 'old', phase: 'active', question: {id:'q', question:'Old question'}, teams:[{name:'Titans',score:500}], player:{id:'p',gameId:'old',teamId:'t',name:'Player',score:50} }, emptyGame())
    const fresh = normalizeState({ id: 'new', status: 'lobby' }, old)
    expect(fresh.question).toBeUndefined()
    expect(fresh.player).toBeUndefined()
    expect(fresh.teams.every(team => team.score === 0 && team.joined === 0)).toBe(true)
    expect(fresh.round).toBe(0)
  })
  it('keeps replaced-session messaging and rejoin availability from the server', () => {
    const ended = normalizeState({id:'old',status:'completed',endedReason:'replaced',newGameAvailable:true},emptyGame('old'))
    expect(ended.phase).toBe('completed')
    expect(ended.endedReason).toBe('replaced')
    expect(ended.newGameAvailable).toBe(true)
  })
  const previous = { ...emptyGame('game-1'), player: { id: 'p', gameId:'game-1', teamId:'t', name:'Harsha', score:380, previousScore:300, hasSubmitted:false } }
  const payload = { phase:'active', question:{id:'q',question:'Test',options:['A','B'],correctAnswer:'B'}, teams:[{name:'Ctrl Alt Defeat',score:900,roundGain:80}],player:{...previous.player,score:460,earnedPoints:80,isCorrect:true,hasSubmitted:true} }
  it('strips correct answers and pending scores from active snapshots', () => {
    const state = normalizeState(payload,previous)
    expect(state.question?.correctAnswer).toBeUndefined();expect(state.player?.earnedPoints).toBeUndefined();expect(state.player?.isCorrect).toBeUndefined();expect(state.player?.score).toBe(380);expect(state.teams[0].score).toBe(0);expect(state.player?.hasSubmitted).toBe(true)
  })
  it('reveals the answer independently from the points', () => {
    const state = normalizeState({...payload,phase:'answer_revealed'},previous)
    expect(state.question?.correctAnswer).toBe('B');expect(state.player?.isCorrect).toBe(true);expect(state.player?.score).toBe(380);expect(state.player?.earnedPoints).toBeUndefined();expect(state.teams[0].score).toBe(0)
  })
  it('displays only server score snapshots after score reveal', () => {
    const state = normalizeState({...payload,phase:'score_revealed'},previous)
    expect(state.player?.score).toBe(460);expect(state.player?.earnedPoints).toBe(80);expect(state.teams[0].score).toBe(900)
  })
  it('does not include pending totals in restored legacy state', () => {
    const state = normalizeState({ player: { id:'p',name:'Harsha' },individual_score:{pending_score:900,total_score:1280},submission_status:{has_submitted:true} },previous)
    expect(state.player?.score).toBe(380);expect(state.player?.hasSubmitted).toBe(true)
  })
})
describe('timestamp timer recovery', () => {
  it('restores remaining time after a refresh using the server timestamp', () => { expect(remainingSeconds('2026-10-06T10:00:00Z',30,Date.parse('2026-10-06T10:00:18Z'))).toBe(12) })
  it('accounts for server time offset', () => { expect(remainingSeconds('2026-10-06T10:00:00Z',30,Date.parse('2026-10-06T09:59:58Z'),20000)).toBe(12) })
  it('never invents a timer or returns a negative value', () => { expect(remainingSeconds(undefined,30,Date.now())).toBeNull();expect(remainingSeconds('bad',30,Date.now())).toBeNull();expect(remainingSeconds('2026-10-06T10:00:00Z',30,Date.parse('2026-10-06T10:01:00Z'))).toBe(0) })
})
