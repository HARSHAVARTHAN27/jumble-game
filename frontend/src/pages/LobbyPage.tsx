import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Clock3, Users, Search, ArrowRight, Star, ChevronDown } from 'lucide-react'
import { useGame } from '../contexts/GameContext'
import { Button, Page, teamClass, ErrorNotice } from '../components/common/UI'
import { AnimatedNumber } from '../components/common/AnimatedNumber'
import { contentService } from '../services/contentService'
import '../lobby.css'

const initials = (name: string) => name.trim().split(/\s+/).slice(0, 2).map(part => part[0]).join('').toUpperCase()
const mascots: Record<string, string> = { coral: 'controller', blue: 'knight', green: 'cloud' }

export default function LobbyPage({ host = false, tools }: { host?: boolean; tools?: ReactNode }) {
  const { state, loading } = useGame()
  const [query, setQuery] = useState(''), [filter, setFilter] = useState('all'), [arrival, setArrival] = useState('')
  const known = useRef<Set<string> | null>(null)
  const room = useRef(state.id)
  const participants = state.participants ?? []
  useEffect(() => {
    if (!state.participants) return
    if (room.current !== state.id) { known.current = null; room.current = state.id; setArrival('') }
    const current = new Set(participants.map(person => person.id))
    if (known.current) {
      const newcomers = participants.filter(person => !known.current!.has(person.id) && !person.isYou)
      if (newcomers.length) setArrival(newcomers.length === 1 ? `${newcomers[0].name} joined the lobby.` : `${newcomers.length} players joined the lobby.`)
    }
    known.current = current
  }, [state.participants, state.id])
  useEffect(() => { if (!arrival) return; const timer = setTimeout(() => setArrival(''), 8000); return () => clearTimeout(timer) }, [arrival])
  const visible = participants.filter(person => (filter === 'all' || person.teamId === filter) && person.name.toLowerCase().includes(query.trim().toLowerCase()))
  if (!host && !state.player && !loading) return <Page className="center-page"><h2>Your team is waiting.</h2><p>Enter your name or employee ID to join the lobby.</p><Link className="button primary" to="/play">Join Lobby<ArrowRight size={18}/></Link></Page>
  return <Page className={`lobby-page illustrated-lobby ${host ? 'host-lobby' : 'player-lobby'}`}>
    <div className="lobby-brand-row">
      <Link to="/" className="lobby-brand" aria-label="Jumble home"><span className="lobby-brand-mark" aria-hidden="true"><i/><i/><i/><i/><i/></span>Jumble</Link>
      {tools}
    </div>
    <header className="lobby-intro">
      <div className="lobby-intro-copy"><h1>The crew is coming together.</h1><p>Players are joining the lobby. Get your team ready!</p></div>
      <div className="lobby-stats">
        <span className="lobby-live"><span aria-hidden="true"/>Lobby Live</span>
        <div className="lobby-count" aria-label={`${state.joined} of ${state.total} players waiting`}><Users aria-hidden="true"/><div><strong><AnimatedNumber value={state.joined}/><span> / </span>{state.total}</strong><span>players waiting</span></div></div>
      </div>
    </header>
    <div className="lobby-waiting"><span className="lobby-clock"><Clock3 aria-hidden="true"/></span><div><strong>The host hasn’t started the game yet.</strong><p>{state.player?.waitingForGame ? 'Waiting for the host to open the game.' : 'We’re waiting for more players to join…'}</p></div></div>
    <div className="lobby-team-grid">{state.teams.map(t => <section key={t.id} className={`lobby-mascot-team ${teamClass(t.name)}`} aria-label={`${t.name} team`}>
      <div className="lobby-card-backdrop" aria-hidden="true"/>
      <img className="lobby-mascot" src={`/images/lobby/${mascots[teamClass(t.name)]}.png`} alt="" width="1280" height="1280" draggable={false}/>
      <div className="lobby-team-info"><h2>{t.name}</h2><span className="lobby-team-count" aria-label={`${t.joined} of ${t.total} players`}><Users aria-hidden="true"/>{t.joined} / {t.total}</span>
        {t.id === state.player?.teamId && <span className="lobby-your-team"><Star size={20} fill="currentColor" aria-hidden="true"/>Your team</span>}
      </div>
    </section>)}</div>
    <details className="lobby-player-details"><summary><span><Users size={18} aria-hidden="true"/>View players <span className="lobby-roster-count">{participants.length}</span></span><ChevronDown size={18} aria-hidden="true"/></summary>
    <section className="crew-roster" aria-labelledby="roster-heading"><div className="crew-roster-header"><div><h2 id="roster-heading">Who’s in the lobby?</h2><p>{!host && state.player ? `You’re playing as ${state.player.name}.` : 'Everyone who has joined, all in one place.'}</p></div><label className="crew-search"><Search size={18} aria-hidden="true"/><span className="sr-only">Search players</span><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search a name…"/></label></div>
      <div className="crew-filters"><button aria-pressed={filter === 'all'} onClick={() => setFilter('all')}>Everyone <span>{participants.length}</span></button>{state.teams.map(t => <button key={t.id} aria-pressed={filter === t.id} onClick={() => setFilter(t.id)}>{t.name} <span>{t.joined}</span></button>)}</div>
      <p className="crew-arrival">Names update automatically.</p>
      <ul className="crew-people" aria-label="Joined players">{visible.map(person => { const memberTeam = state.teams.find(t => t.id === person.teamId); return <li key={person.id}><span className={`crew-avatar ${memberTeam ? teamClass(memberTeam.name) : ''}`}>{initials(person.name)}</span><div><strong>{person.name}</strong><span>{memberTeam?.name}</span></div><span className="crew-person-status">{person.isYou ? 'YOU' : 'Joined'}</span></li> })}</ul>
      {!visible.length && <div className="crew-empty"><Users size={28} aria-hidden="true"/><strong>{participants.length ? 'No players match that search.' : loading ? 'Gathering the lobby…' : 'Be the first to join.'}</strong><p>{participants.length ? 'Try another name or team.' : 'Joined names will appear here automatically.'}</p></div>}
    </section></details><div className="sr-only" role="status" aria-live="polite">{arrival}</div>{host && <HostStart/>}
  </Page>
}
function HostStart() {
  const { state, hostAction } = useGame()
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [ready, setReady] = useState(false), [checking, setChecking] = useState(true)
  useEffect(() => { let alive = true; contentService.validate(state.id).then(result => { if (alive) setReady(result.ready) }).catch(e => { if (alive) setError(e.message) }).finally(() => { if (alive) setChecking(false) }); return () => { alive = false } }, [state.id])
  const start = async () => { setBusy(true); setError(''); try { await hostAction('start') } catch (e) { setError(e instanceof Error ? e.message : 'Unable to start.') } finally { setBusy(false) } }
  return <div className="lobby-start">{error && <ErrorNotice message={error}/>}<Link className="button secondary" to="/control/content">Edit game content</Link><Button busy={busy} onClick={start} disabled={checking || !ready || state.teams.some(t => t.joined < 2) || state.phase !== 'lobby'}>Let’s Play<ArrowRight size={21}/></Button><p>{checking ? 'Checking game content…' : !ready ? 'Complete and save all six rounds before starting.' : state.teams.some(t => t.joined < 2) ? 'Each team needs at least two players for Draw & Guess.' : 'Everyone stays in. Every round counts.'}</p></div>
}
