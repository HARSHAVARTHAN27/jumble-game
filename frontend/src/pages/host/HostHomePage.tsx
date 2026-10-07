import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, Radio, Users, Layers3, Trophy } from 'lucide-react'
import { Page, Button, ErrorNotice } from '../../components/common/UI'
import { GameArt } from '../../components/common/GameArt'
import { useGame } from '../../contexts/GameContext'
export default function HostHomePage() {
  const { state, hostAction } = useGame(); const navigate = useNavigate(); const [busy, setBusy] = useState(false); const [error, setError] = useState('')
  const create = async () => { setBusy(true); setError(''); try { await hostAction('create'); navigate('/control/content') } catch (e) { setError(e instanceof Error ? e.message : 'Unable to create game.') } finally { setBusy(false) } }
  return <Page className="host-home"><div><span className="eyebrow"><Radio size={15}/> YOU’RE THE HOST</span><h1>Set the stage.<br/><span>Bring the energy.</span></h1><p>You handle the reveals. We’ll handle the suspense.<br/>Let’s make this meeting a little more memorable.</p><div className="host-facts"><span><Users size={19}/>{state.total} imported players</span><span><Layers3 size={19}/>6 rounds</span><span><Trophy size={19}/>1 winning team</span></div>{error && <ErrorNotice message={error}/>}<Button onClick={create} busy={busy}>Create Game<ArrowRight size={20}/></Button>{state.id && <button className="back-link" onClick={() => navigate(state.phase === 'completed' ? '/control/results' : state.phase === 'lobby' ? '/control/lobby' : '/control/game')}>Continue active game<ArrowRight size={16}/></button>}<p className="muted small-text">Players join with their name. No codes, no fuss.</p></div><GameArt/></Page>
}
