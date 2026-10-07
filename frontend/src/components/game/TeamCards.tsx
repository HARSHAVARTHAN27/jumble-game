import { motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import { Check, Users } from 'lucide-react'
import type { Team } from '../../types/game'
import { Progress, TeamIcon, teamClass } from '../common/UI'
import { AnimatedNumber } from '../common/AnimatedNumber'
export function TeamCards({ teams, ownId, host = false }: { teams: Team[]; ownId?: string; host?: boolean }) {
  const previous = useRef(new Map(teams.map(t => [t.id,t.joined])))
  const [joined, setJoined] = useState<string[]>([])
  useEffect(() => {
    const changed = teams.filter(t => previous.current.has(t.id) && t.joined > (previous.current.get(t.id) ?? 0)).map(t => t.id)
    previous.current = new Map(teams.map(t => [t.id,t.joined]))
    if (changed.length) setJoined(changed)
    const timeout = setTimeout(() => setJoined([]),1400)
    return () => clearTimeout(timeout)
  }, [teams])
  return <div className={`team-cards ${host ? 'host-teams' : ''}`}>{teams.map((team, index) => <motion.div key={team.id} layout className={`team-card ${teamClass(team.name)} ${ownId === team.id ? 'own-team' : ''} ${joined.includes(team.id) ? 'new-join' : ''}`} initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.1 }}>{joined.includes(team.id) && <span className="join-bubble">+1</span>}<div className="team-card-top"><span className="team-symbol"><TeamIcon name={team.name} size={host ? 36 : 25}/></span>{ownId === team.id && <span className="your-team"><Check size={12}/>YOUR TEAM</span>}</div><h3>{team.name}</h3><div className="team-count"><strong><AnimatedNumber value={team.joined}/></strong><span>/ {team.total}</span><small>ready to play</small></div><Progress value={team.joined} max={team.total}/>{host && <div className="team-members">{team.members.length ? team.members.map(name => <div key={name}><span className="member-avatar">{name.slice(0, 1)}</span>{name}<Check size={14}/></div>) : <div className="empty-members"><Users size={22}/><p>Saving a spot for your people.</p></div>}</div>}</motion.div>)}</div>
}
