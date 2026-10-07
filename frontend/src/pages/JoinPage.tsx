import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, LockKeyhole, Sparkles, UserRound } from 'lucide-react'
import { useGame } from '../contexts/GameContext'
import { ApiError } from '../services/api'
import { Button, ErrorNotice, Page } from '../components/common/UI'
import { GameArt } from '../components/common/GameArt'

export default function JoinPage() {
  const { join } = useGame()
  const navigate = useNavigate()
  const [identifier, setIdentifier] = useState('')
  const [code, setCode] = useState('')
  const [duplicate, setDuplicate] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const enter = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!identifier.trim() || busy) return
    setBusy(true); setError('')
    try {
      await join(identifier.trim(), code.trim() || undefined)
      navigate('/lobby', { replace: true })
    } catch (e) {
      if (e instanceof ApiError && e.code === 'DUPLICATE_EMPLOYEE_NAME') setDuplicate(true)
      setError(e instanceof Error ? e.message : 'Unable to find your team.')
    } finally { setBusy(false) }
  }
  return <Page className="join-page"><div className="join-illustration"><GameArt/><div className="join-caption"><h2>Great minds play together.</h2><p>Find your people. Bring your A-game.</p></div></div><section className="form-panel">
    <button className="back-link" onClick={() => navigate('/')}><ArrowLeft size={17}/>Back to the fun</button>
    <div className="state-icon purple"><Sparkles size={30}/></div>
    <span className="eyebrow">YOUR TEAM IS WAITING</span><h1>Ready to play?</h1>
    <p>Enter your name or employee ID.<br/>We’ll find your team and take you to the lobby.</p>
    <form onSubmit={enter}>
      <label htmlFor="player-identifier">Your name or employee ID</label>
      <div className="input-wrap"><UserRound size={20}/><input id="player-identifier" value={identifier} onChange={e => { setIdentifier(e.target.value); setError(''); setDuplicate(false); setCode('') }} placeholder="e.g. Harshavarthan or GIPL042" autoComplete="off" autoCapitalize="none" spellCheck={false} maxLength={100} required autoFocus disabled={busy}/></div>
      {duplicate && <><label htmlFor="employee-code">Employee ID</label><div className="input-wrap"><input id="employee-code" value={code} onChange={e => setCode(e.target.value)} placeholder="e.g. GIPL042" autoComplete="off" maxLength={50} required autoFocus disabled={busy}/></div></>}
      {error && <ErrorNotice message={error}/>}
      <Button type="submit" busy={busy} disabled={!identifier.trim() || (duplicate && !code.trim())}>{busy ? 'Joining your team…' : 'Join Lobby'}{!busy && <ArrowRight size={20}/>}</Button>
    </form>
    <span className="form-note"><LockKeyhole size={14}/>Your team is assigned. Just bring yourself.</span>
  </section></Page>
}
