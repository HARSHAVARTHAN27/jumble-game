import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, LockKeyhole, Hourglass } from 'lucide-react'
import { useGame } from '../contexts/GameContext'
import type { HostAction } from '../contexts/GameContext'
import { Button, ErrorNotice, Page, TeamBadge } from '../components/common/UI'
import { GameRenderer } from '../components/game/GameRenderer'
import { Timer } from '../components/game/Timer'
import { ScoreReveal } from '../components/game/ScoreReveal'
import { TeamLeaderboard } from '../components/game/TeamLeaderboard'
import { ROUND_RULES } from '../types/content'
import { contentService } from '../services/contentService'
import { post, query } from '../services/api'
import type { DrawingStroke } from '../types/game'
import { useCountdown } from '../hooks/useCountdown'

export default function PlayerGamePage({ host = false }: { host?: boolean }) {
  const { state } = useGame(), team = state.teams.find(t => t.id === state.player?.teamId)
  if (!host && !state.player) return <Page className="center-page"><h2>First, find your team.</h2><Link to="/play" className="button primary">Join Game<ArrowRight size={18}/></Link></Page>
  return <Page className={`game-page ${host ? 'host-game' : 'player-game'}`}><div className="round-header"><div><span className="eyebrow">ROUND {state.round || 1} OF 6</span><h2>{state.roundName}</h2></div>{host ? <span className="host-label">HOST VIEW</span> : team && <TeamBadge name={team.name}/>}</div>
    <div className={host ? 'host-game-grid' : ''}><section className="game-panel">
      {(state.phase === 'intro' || state.phase === 'between') && <div className="round-intro"><span className="eyebrow">{state.phase === 'between' ? 'NEXT ROUND' : state.question?.isDemo ? 'DEMO · PRACTICE' : `QUESTION ${state.question?.number ?? 1} / ${state.question?.scoredCount ?? 6}`}</span><h1>{state.roundName}</h1><p>{state.question?.instructions || ROUND_RULES[state.round - 1]}</p>{state.question?.isDemo && <p>Practice awards 0 points and does not affect scores.</p>}{state.phase === 'between' && <TeamLeaderboard teams={state.teams}/>}<p>{state.question?.lockAfterAttempt ? 'Submit one answer per team.' : 'Answer before time runs out.'}</p>{host ? <HostControls/> : <span className="waiting-label">Waiting for the host to start.</span>}</div>}
      {(state.phase === 'active' || state.phase === 'ended') && <LiveQuestion key={state.question?.id} host={host}/>}
      {(state.phase === 'score_revealed' || state.phase === 'answer_revealed') && <><div className="question-answer"><span className="eyebrow">{state.question?.isDemo ? 'DEMO' : `QUESTION ${state.question?.number} / ${state.question?.scoredCount ?? 6}`} · ANSWER</span><strong>{state.question?.correctAnswer}</strong></div>{state.question?.isDemo ? <p className="content-success">Practice complete · 0 points. Scores are unchanged.</p> : <ScoreReveal host={host}/>}{host ? <HostControls/> : <p className="waiting-label">Your team score is up to date. Waiting for the next question.</p>}</>}
      {state.phase === 'lobby' && <div className="round-intro"><Hourglass size={45}/><h2>The fun starts soon.</h2><Link to={host ? '/control/lobby' : '/lobby'} className="button secondary">Back to Lobby</Link></div>}
    </section>{host && <HostPanel/>}</div>
  </Page>
}

function LiveQuestion({ host }: { host: boolean }) {
  const { state, submit, clockOffset, refresh } = useGame(), q = state.question, player = state.player
  const [answer, setAnswer] = useState(''), [busy, setBusy] = useState(false), [error, setError] = useState(''), [message, setMessage] = useState('')
  const remaining = useCountdown(q?.startedAt, q?.durationSeconds ?? 30, clockOffset)
  const prep = q?.subphase === 'prepare', artist = q?.questionData?.isArtist, closed = state.phase !== 'active' || remaining === 0
  const send = async () => { setBusy(true); setError(''); try { await submit(answer.trim()); setAnswer(''); setMessage(q?.lockAfterAttempt ? 'Team answer received and locked.' : 'Answer received. You may retry until your team solves the question.') } catch (e) { setError(e instanceof Error ? e.message : 'Unable to submit.') } finally { setBusy(false) } }
  const stroke = async (value: DrawingStroke) => { if (!q || !player) return; await post('/api/player/question/' + encodeURIComponent(q.id) + '/stroke' + query({ game_id: state.id, player_id: player.id }), value); await refresh() }
  if (!q) return <div className="submission-state"><h2>Waiting for the next challenge.</h2></div>
  return <div className="question-content"><div className="question-meta"><span className="eyebrow">{q.isDemo ? 'DEMO · PRACTICE' : `QUESTION ${q.number} / ${q.scoredCount ?? 6}`} · {q.durationSeconds} SEC {prep ? 'MEMORIZATION / PREPARATION' : 'ANSWERS'}</span><Timer/></div><h1>{q.question}</h1>{q.instructions && <p className="round-rule">{q.instructions}</p>}
    {prep && remaining === 0 ? <p role="status">Opening the answering phase…</p> : <GameRenderer question={q} selected={answer} onSelect={setAnswer} disabled={busy || closed || player?.hasSubmitted} host={host} clockOffset={clockOffset} teamNames={Object.fromEntries(state.teams.map(t => [t.id, t.name]))} onStroke={stroke}/>}
    {host ? <HostControls/> : player?.hasSubmitted ? <p className="content-success" role="status"><LockKeyhole size={18}/>Your team answer is locked. Results appear when the question closes.</p> : !prep && !artist && <><Button busy={busy} disabled={!answer.trim() || closed} onClick={() => void send()}>Submit answer<ArrowRight size={18}/></Button><p className="submit-note">{q.lockAfterAttempt ? 'One answer per team.' : 'Repeated attempts are allowed. Team marks count once.'}</p></>}
    {error && <ErrorNotice message={error}/>}<p role="status" className="small-text">{message}</p>
  </div>
}

function HostPanel() {
  const { state, refresh } = useGame(), [error, setError] = useState(''), [busy, setBusy] = useState(false)
  const review = async (id: string, correct: boolean) => { setBusy(true); setError(''); try { await contentService.review(state.id, id, correct); await refresh() } catch (e) { setError(e instanceof Error ? e.message : 'Unable to review.') } finally { setBusy(false) } }
  const reassign = async (teamId: string, playerId: string) => { if (!playerId) return; setBusy(true); setError(''); try { await contentService.reassign(state.id, teamId, playerId); await refresh() } catch (e) { setError(e instanceof Error ? e.message : 'Unable to select artist.') } finally { setBusy(false) } }
  return <aside className="submission-panel"><span className="eyebrow">HOST SCOREBOARD</span><h3>Every team. Every mark.</h3>{state.question?.hostAnswer && <p className="host-answer">HOST ONLY · Correct answer: <strong>{state.question.hostAnswer}</strong></p>}<div className="host-score-list">{state.teams.map(t => <div key={t.id}><TeamBadge name={t.name}/><strong>{t.score}</strong><small>{state.phase === 'score_revealed' ? `+${t.roundGain} this question` : `${t.submitted} players answered`}</small></div>)}</div>
    {state.question?.gameType === 'drawing' && state.phase === 'active' && <div className="artist-controls"><h4>Selected artists</h4>{state.teams.map(t => <label key={t.id}>{t.name}<select value={state.question?.questionData?.artists?.[t.id] ?? ''} disabled={busy} onChange={e => void reassign(t.id, e.target.value)}><option value="">Select artist</option>{state.participants?.filter(p => p.teamId === t.id).map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>)}<p>Reassigning preserves the question deadline.</p></div>}
    {['active', 'score_revealed'].includes(state.phase) && ['text', 'output', 'mcq', 'expression'].includes(state.question?.questionType ?? '') && <div className="grading-review"><h4>Review text answers</h4><p>Corrections update both scorecards immediately.</p>{state.reviewSubmissions?.map(s => <div key={s.id}><strong>{state.participants?.find(p => p.id === s.playerId)?.name ?? 'Player'}</strong><pre>{s.answer}</pre><small>{s.elapsed.toFixed(1)} sec · {s.correct ? 'Correct' : 'Incorrect'}</small><button className="button secondary" disabled={busy || state.phase !== 'score_revealed' || !['text', 'output'].includes(state.question?.questionType ?? '')} onClick={() => void review(s.id, !s.correct)}>{s.correct ? 'Mark incorrect' : 'Accept answer'}</button></div>)}</div>}
    {error && <ErrorNotice message={error}/>}<p className="submit-note">Marks update automatically after every question.</p>
  </aside>
}

export function HostControls() {
  const { state, hostAction } = useGame(), [busy, setBusy] = useState(false), [error, setError] = useState('')
  useEffect(() => setError(''), [state.phase])
  const controls: Partial<Record<typeof state.phase, { label: string; action: HostAction }>> = {
    intro: { label: state.question?.isDemo ? 'Start Demo' : state.question?.number === 1 ? 'Start Round · Question 1' : 'Start Question', action: 'question' }, active: { label: 'End Question & Show Scores', action: 'end' },
    ended: { label: 'Show Scores', action: 'scores' }, answer_revealed: { label: 'Show Scores', action: 'scores' },
    score_revealed: { label: state.isLastQuestion ? 'Finish Game' : state.question?.isDemo ? 'Continue · Start Round' : state.question?.number === state.question?.scoredCount ? 'End Round · Round Results' : 'Next Question', action: state.isLastQuestion ? 'finish' : 'next' },
    between: { label: `Start Round ${state.round}`, action: 'round' },
  }
  const current = controls[state.phase]
  const run = async () => { if (!current) return; setBusy(true); setError(''); try { await hostAction(current.action) } catch (e) { setError(e instanceof Error ? e.message : 'Unable to continue.') } finally { setBusy(false) } }
  return <div className="host-controls">{error && <ErrorNotice message={error}/>} {state.phase === 'active' && state.question?.gameType === 'connection' && <Button disabled={busy || (state.question.questionData?.clues?.length ?? 0) >= 4} onClick={() => { setBusy(true); void contentService.clue(state.id).catch(e => setError(e.message)).finally(() => setBusy(false)) }}>Reveal next clue</Button>} {current && <Button busy={busy} onClick={() => void run()}>{current.label}<ArrowRight size={20}/></Button>}<span className="submit-note">Timers close questions and award marks automatically.</span></div>
}
