import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'
class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() { if (this.state.failed) return <main className="center-page"><h1>Let’s get you back in.</h1><p>Something unexpected happened. Your game session is saved.</p><button className="button primary" onClick={() => window.location.reload()}>Rejoin Game</button></main>; return this.props.children }
}
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><ErrorBoundary><BrowserRouter><App/></BrowserRouter></ErrorBoundary></React.StrictMode>)
