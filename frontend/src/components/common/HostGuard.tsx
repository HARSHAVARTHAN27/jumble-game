import { useEffect, useState } from 'react'
import type { ReactNode, FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { supabase } from '../../services/supabase'
import { request } from '../../services/api'
import { Brand, Button, ErrorNotice, Loading } from './UI'

export function HostGuard({ children }: { children: ReactNode }) {
  const [allowed, setAllowed] = useState(false)
  const [checking, setChecking] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    let alive = true
    const verify = async () => {
      try { await request('/api/host/access'); if (alive) { setAllowed(true); setError('') } }
      catch { if (alive) setAllowed(false) }
      finally { if (alive) setChecking(false) }
    }
    void verify()
    const listener = supabase?.auth.onAuthStateChange(() => { setTimeout(() => { if (alive) void verify() }, 0) })
    return () => { alive = false; listener?.data.subscription.unsubscribe() }
  }, [])
  const signIn = async (event: FormEvent) => {
    event.preventDefault()
    if (!supabase) return
    setBusy(true); setError('')
    try {
      const result = await supabase.auth.signInWithPassword({ email, password })
      if (result.error) throw new Error('Sign-in failed. Check your account details.')
      await request('/api/host/access')
      setAllowed(true)
    } catch (e) { setError(e instanceof Error ? e.message : 'Access denied.') }
    finally { setBusy(false); setPassword('') }
  }
  if (checking) return <Loading label="Checking access…"/>
  if (allowed) return children
  return <div className="app"><header className="site-header"><Brand/></header><main className="center-page">
    <h1>Restricted access</h1><p>This area requires an authorized account.</p>
    {supabase ? <form className="form-panel control-sign-in" onSubmit={signIn}>
      <label htmlFor="control-email">Email</label><div className="input-wrap"><input id="control-email" type="email" autoComplete="username" required value={email} onChange={e => setEmail(e.target.value)}/></div>
      <label htmlFor="control-password">Password</label><div className="input-wrap"><input id="control-password" type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)}/></div>
      {error && <ErrorNotice message={error}/>}<Button busy={busy} type="submit">Sign in</Button>
    </form> : <p>Account sign-in is not configured yet.</p>}
    <Link to="/" className="back-link">Back to Home</Link>
  </main></div>
}
