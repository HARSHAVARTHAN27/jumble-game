import { motion } from 'framer-motion'
import { Crown, ArrowUp, ArrowDown, Minus } from 'lucide-react'
import type { Team } from '../../types/game'
import { TeamIcon, teamClass } from '../common/UI'
import { AnimatedNumber } from '../common/AnimatedNumber'
export function TeamLeaderboard({ teams, compact = false }: { teams: Team[]; compact?: boolean }) {
  const sorted = [...teams].sort((a, b) => b.score - a.score)
  return <div className={`leaderboard ${compact ? 'compact' : ''}`}>
    {sorted.map((team, index) => {
      const move = (team.previousRank ?? index + 1) - index - 1
      return <motion.div layout transition={{ type: 'spring', stiffness: 110, damping: 20 }} key={team.id} className={`leader-row ${teamClass(team.name)} ${index === 0 ? 'leader' : ''}`}><span className="rank">{index === 0 ? <Crown size={24}/> : `0${index + 1}`}</span><span className="team-symbol"><TeamIcon name={team.name} size={28}/></span><div className="leader-name"><h3>{team.name}</h3><small>{team.roundGain > 0 ? `+${team.roundGain} this round` : 'In it together'}</small></div><span className="rank-change" aria-label={move > 0 ? `Up ${move} places` : move < 0 ? `Down ${-move} places` : 'Rank unchanged'}>{move > 0 ? <ArrowUp size={14}/> : move < 0 ? <ArrowDown size={14}/> : <Minus size={14}/>} {move !== 0 ? Math.abs(move) : ''}</span><strong className="leader-score"><AnimatedNumber value={team.score} from={Math.max(0, team.score - team.roundGain)}/><small>pts</small></strong></motion.div>
    })}
  </div>
}
