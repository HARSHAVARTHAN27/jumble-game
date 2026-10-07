import { useGame } from '../../contexts/GameContext'
import { TeamBadge } from '../common/UI'
import { AnimatedNumber } from '../common/AnimatedNumber'
export function ScoreReveal({ host = false }: { host?: boolean }) {
  const { state } = useGame()
  return <div className="score-reveal"><span className="eyebrow">QUESTION COMPLETE · TEAM SCORECARD</span><h2>{host ? 'The marks are in.' : 'See your team climb.'}</h2><div className="question-scorecards">{[...state.teams].sort((a, b) => b.score - a.score).map(team => <section key={team.id} className={state.player?.teamId === team.id ? 'your-scorecard' : ''}><TeamBadge name={team.name}/>{state.player?.teamId === team.id && <span className="eyebrow">YOUR TEAM</span>}<div><strong>+{team.roundGain}</strong><span>this question</span></div><p>Total marks <b><AnimatedNumber value={team.score}/></b></p></section>)}</div><p className="submit-note">One scoring answer per team. Host grading corrections update these totals.</p></div>
}
