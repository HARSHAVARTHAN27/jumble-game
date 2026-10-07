import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Plus, Save, ArrowRight, ArrowUp, ArrowDown, Trash2, Eye, CheckCircle2, Clock3 } from 'lucide-react'
import { Page, Button, ErrorNotice, Loading } from '../../components/common/UI'
import { useGame } from '../../contexts/GameContext'
import { contentService } from '../../services/contentService'
import { blankContent, blankQuestion, ROUND_NAMES, ROUND_RULES } from '../../types/content'
import type { GameContent, ContentQuestion, ContentError } from '../../types/content'
import { GameRenderer } from '../../components/game/GameRenderer'
import type { Question } from '../../types/game'

export default function GameContentPage() {
  const { state } = useGame()
  const navigate = useNavigate()
  const [content, setContent] = useState<GameContent>(blankContent), [round, setRound] = useState(0), [index, setIndex] = useState(0)
  const [loading, setLoading] = useState(true), [busy, setBusy] = useState(false), [dirty, setDirty] = useState(false), [saved, setSaved] = useState(false)
  const [error, setError] = useState(''), [errors, setErrors] = useState<ContentError[]>([]), [preview, setPreview] = useState(false), [images, setImages] = useState<Record<string, string>>({})
  const locked = state.phase !== 'lobby'
  useEffect(() => {
    if (!state.id) { setLoading(false); return }
    let alive = true
    setLoading(true)
    contentService.get(state.id).then(doc => { if (alive) { setContent(doc); setDirty(false); setSaved(doc.version > 0) } }).catch(e => { if (alive) setError(e.message) }).finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [state.id])
  useEffect(() => { const warn = (e: BeforeUnloadEvent) => { if (dirty) e.preventDefault() }; window.addEventListener('beforeunload', warn); return () => window.removeEventListener('beforeunload', warn) }, [dirty])
  const r = content.rounds[round], q = r.questions[index]
  const imagePaths = [...(q?.data.cells ?? []), ...(q?.data.clues ?? [])].filter(c => c.startsWith('image:')).join('|')
  useEffect(() => {
    let alive = true
    for (const cell of imagePaths.split('|').filter(Boolean)) {
      contentService.image(state.id, cell.slice(6)).then(result => { if (alive) setImages(old => ({ ...old, [cell]: result.url })) }).catch(() => {})
    }
    return () => { alive = false }
  }, [imagePaths, state.id])
  const change = (next: GameContent) => { setContent(next); setDirty(true); setSaved(false); setErrors([]) }
  const patch = (updates: Partial<ContentQuestion>) => change({ ...content, rounds: content.rounds.map((r, i) => i === round ? { ...r, questions: r.questions.map((v, j) => j === index ? { ...v, ...updates } : v) } : r) })
  const patchData = (updates: ContentQuestion['data']) => { if (q) patch({ data: { ...q.data, ...updates } }) }
  const add = () => { const next = blankQuestion(r.gameType); change({ ...content, rounds: content.rounds.map((r, i) => i === round ? { ...r, questions: [...r.questions, next] } : r) }); setIndex(r.questions.length) }
  const remove = () => { change({ ...content, rounds: content.rounds.map((r, i) => i === round ? { ...r, questions: r.questions.filter((_, j) => j !== index) } : r) }); setIndex(Math.max(0, index - 1)) }
  const move = (direction: number) => { const next = index + direction; if (next < 0 || next >= r.questions.length) return; const questions = [...r.questions]; [questions[index], questions[next]] = [questions[next], questions[index]]; change({ ...content, rounds: content.rounds.map((r, i) => i === round ? { ...r, questions } : r) }); setIndex(next) }
  const save = async () => { setBusy(true); setError(''); try { const result = await contentService.save(state.id, content); setContent({ version: result.version, rounds: result.rounds }); setErrors(result.errors); setDirty(false); setSaved(true); return true } catch (e) { setError(e instanceof Error ? e.message : 'Unable to save.'); return false } finally { setBusy(false) } }
  const openLobby = async () => { if (!dirty || await save()) navigate('/control/lobby') }
  const upload = async (field: 'cells' | 'clues', itemIndex: number, file: File) => {
    if (!q) return
    const id = q.id; setBusy(true); setError('')
    try {
      const result = await contentService.upload(state.id, file)
      setImages(old => ({ ...old, [result.cell]: result.url }))
      setContent(old => ({ ...old, rounds: old.rounds.map(r => ({ ...r, questions: r.questions.map(question => question.id === id ? { ...question, data: withEntry(question.data, field, itemIndex, result.cell) } : question) })) }))
      setDirty(true); setSaved(false)
    } catch (e) { setError(e instanceof Error ? e.message : 'Upload failed.') } finally { setBusy(false) }
  }
  if (loading) return <Loading label="Loading your game content…"/>
  if (!state.id) return <Page className="center-page"><h1>Create a game first.</h1><Link className="button primary" to="/control">Host home<ArrowRight size={18}/></Link></Page>
  return <Page className="content-page"><header className="content-header"><div><span className="eyebrow">HOST STUDIO · SIX ROUNDS</span><h1>Build the challenge.</h1><p>Add your questions. Preview the experience. Bring your teams together.</p></div><div className="content-header-actions"><span className={`save-status ${dirty ? 'unsaved' : ''}`} role="status">{locked ? 'Content locked' : dirty ? 'Unsaved changes' : saved ? 'Draft saved' : 'New draft'}</span><Button disabled={locked || busy} onClick={() => { setBusy(true); void contentService.bank(state.id).then(doc => { change(doc); setRound(0); setIndex(0) }).catch(e => setError(e.message)).finally(() => setBusy(false)) }}>Load v2 question bank</Button><Button onClick={() => void save()} busy={busy} disabled={locked || !dirty}>Save draft<Save size={18}/></Button><Link className="button secondary" to="/control/lobby" onClick={e => { if (dirty) { e.preventDefault(); void openLobby() } }}>Open lobby<ArrowRight size={18}/></Link></div></header>
    {error && <ErrorNotice message={error}/>}
    {saved && !errors.length && <p className="content-success" role="status"><CheckCircle2 size={18}/>Draft saved. All six rounds will be checked again when you start.</p>}
    {!!errors.length && <div className="content-errors" role="alert"><strong>Draft saved. Complete these fields before starting:</strong><ul>{errors.map(e => <li key={e.path}>{e.path.replace(/rounds\.(\d+)\.questions\.(\d+)/, (_, a, b) => `Round ${Number(a) + 1}, question ${Number(b) + 1}`).replace(/rounds\.(\d+)/, (_, a) => `Round ${Number(a) + 1}`)}: {e.message}</li>)}</ul></div>}
    <nav className="round-tabs" aria-label="Game rounds">{content.rounds.map((r, i) => <button key={r.gameType} aria-current={round === i ? 'step' : undefined} onClick={() => { setRound(i); setIndex(0); setPreview(false) }}><span>{i + 1}</span><strong>{ROUND_NAMES[i]}</strong><small>{r.questions.filter(q => !q.isDemo).length} questions{r.questions.some(q => q.isDemo) ? ' + demo' : ''}</small></button>)}</nav>
    <div className="content-layout"><aside className="question-sidebar"><div><h2>Questions</h2><button className="icon-button" aria-label="Add question" onClick={add} disabled={locked || busy}><Plus size={20}/></button></div>{r.questions.map((v, j) => <button className={index === j ? 'selected-question' : ''} key={v.id} onClick={() => { setIndex(j); setPreview(false) }}><span>{v.isDemo ? 'DEMO' : r.questions.slice(0, j + 1).filter(q => !q.isDemo).length}</span><strong>{v.prompt || 'Untitled question'}</strong></button>)}{!r.questions.length && <p>No questions yet. Add the first challenge.</p>}</aside>
      <section className="question-editor"><header><div><span className="eyebrow">ROUND {round + 1}</span><h2>{ROUND_NAMES[round]}</h2></div><span className="duration-pill"><Clock3 size={16}/>{q?.answerTime ?? 30} sec answers</span></header><p className="round-rule">{q?.instructions || ROUND_RULES[round]}</p>
        {!q ? <div className="editor-empty"><h3>Make it your own.</h3><p>Add a question to start building this round.</p><Button onClick={add} disabled={locked}>Add question<Plus size={18}/></Button></div> : <>
          <div className="question-toolbar"><strong>{q.isDemo ? 'DEMO · 0 POINTS' : `Question ${r.questions.slice(0, index + 1).filter(q => !q.isDemo).length} / ${r.questions.filter(q => !q.isDemo).length}`}</strong><button className="icon-button" aria-label="Move question up" disabled={locked || index === 0} onClick={() => move(-1)}><ArrowUp size={18}/></button><button className="icon-button" aria-label="Move question down" disabled={locked || index === r.questions.length - 1} onClick={() => move(1)}><ArrowDown size={18}/></button><button className="icon-button" aria-label="Delete question" disabled={locked} onClick={remove}><Trash2 size={18}/></button><button className="button secondary" onClick={() => setPreview(v => !v)}><Eye size={18}/>{preview ? 'Close preview' : 'Preview'}</button></div>
          <fieldset disabled={locked || busy} className="content-fields"><label className="checkbox-field"><input type="checkbox" checked={Boolean(q.isDemo)} onChange={e => patch({ isDemo: e.target.checked })}/>Demo · always 0 points</label><div className="field-pair"><label>Answer seconds<input type="number" min={1} max={300} value={q.answerTime ?? 30} onChange={e => patch({ answerTime: Number(e.target.value) })}/></label>{['memory', 'drawing'].includes(r.gameType) && <label>Preparation seconds<input type="number" min={1} max={120} value={q.memoryTime ?? 10} onChange={e => patch({ memoryTime: Number(e.target.value) })}/></label>}</div>{q.data.image && <img className="bank-visual" src={q.data.image} alt="Question bank visual"/>}
            <label>{r.gameType === 'drawing' ? 'Secret card (artist and host only)' : 'Question'}<textarea rows={3} value={q.prompt} onChange={e => patch({ prompt: e.target.value })} maxLength={4000}/></label>
            {['memory', 'technical'].includes(r.gameType) && <label>Answer format<select value={q.answerType} onChange={e => patch({ answerType: e.target.value as ContentQuestion['answerType'], options: e.target.value === 'mcq' && !q.options.length ? ['', '', '', ''] : q.options })}><option value="mcq">Multiple choice</option><option value="text">Short text</option>{r.gameType === 'technical' && <option value="output">Code / output</option>}</select></label>}
            {r.gameType === 'memory' && <><div className="field-pair"><label>Grid rows<input type="number" min={1} max={6} value={q.data.rows} onChange={e => { const rows = Math.min(6, Math.max(1, Number(e.target.value))); patchData({ rows, cells: Array.from({ length: rows * (q.data.cols ?? 3) }, (_, i) => q.data.cells?.[i] ?? '') }) }}/></label><label>Grid columns<input type="number" min={1} max={6} value={q.data.cols} onChange={e => { const cols = Math.min(6, Math.max(1, Number(e.target.value))); patchData({ cols, cells: Array.from({ length: cols * (q.data.rows ?? 3) }, (_, i) => q.data.cells?.[i] ?? '') }) }}/></label></div><div className="grid-cell-editor">{q.data.cells?.map((cell, i) => <div key={i}><label>Cell {i + 1}<input value={cell.startsWith('image:') ? 'Uploaded image' : cell} readOnly={cell.startsWith('image:')} onChange={e => patchData({ cells: q.data.cells?.map((v, j) => j === i ? e.target.value : v) })}/></label>{images[cell] && <img src={images[cell]} alt={`Cell ${i + 1}`}/>}<label className="image-upload">Upload image<input type="file" accept="image/png,image/jpeg,image/webp" onChange={e => { const file = e.target.files?.[0]; if (file) void upload('cells', i, file); e.target.value = '' }}/></label>{cell.startsWith('image:') && <button type="button" onClick={() => patchData({ cells: q.data.cells?.map((v, j) => j === i ? '' : v) })}>Remove image</button>}</div>)}</div></>}
            {r.gameType === 'emoji' && <label>Emoji puzzle<input value={q.data.puzzle ?? ''} onChange={e => patchData({ puzzle: e.target.value })} placeholder="🕷️ + 👨"/></label>}
            {r.gameType === 'connection' && <div className="clue-editor">{q.data.clues?.map((clue, i) => { const isImage = clue.startsWith('image:'); return <div key={i}><label>Clue {i + 1} · {i * 7} seconds<input value={isImage ? 'Uploaded image' : clue} readOnly={isImage} onChange={e => patchData({ clues: q.data.clues?.map((v, j) => j === i ? e.target.value : v) })}/></label>{images[clue] && <img src={images[clue]} alt={`Clue ${i + 1}`}/>}<label className="image-upload">Upload image<input type="file" accept="image/png,image/jpeg,image/webp" onChange={e => { const file = e.target.files?.[0]; if (file) void upload('clues', i, file); e.target.value = '' }}/></label>{isImage && <button type="button" onClick={() => patchData({ clues: q.data.clues?.map((v, j) => j === i ? '' : v) })}>Remove image</button>}</div> })}</div>}
            {r.gameType === 'target' && <><label>Target number<input type="number" min={1} max={1000000} value={q.data.target ?? 50} onChange={e => patchData({ target: Number(e.target.value) })}/></label><NumberList key={q.id} numbers={q.data.numbers ?? []} onChange={numbers => patchData({ numbers })}/></>}
            {r.gameType === 'technical' && <><label>Code snippet (optional)<textarea className="code-answer" rows={5} value={q.data.code ?? ''} onChange={e => patchData({ code: e.target.value })}/></label>{(index === r.questions.length - 1 || q.hard) && <label className="checkbox-field"><input type="checkbox" checked={q.hard} onChange={e => patch({ hard: e.target.checked })}/>Final hard question · 50 base marks</label>}</>}
            {q.answerType === 'mcq' ? <><label>Answer choices (one per line)<textarea rows={4} value={q.options.join('\n')} onChange={e => patch({ options: e.target.value.split('\n') })}/></label><label>Correct choice<select value={q.acceptedAnswers[0] ?? ''} onChange={e => patch({ acceptedAnswers: [e.target.value] })}><option value="">Select the correct choice</option>{q.options.filter(Boolean).map((option, i) => <option key={i} value={option}>{option}</option>)}</select></label></> : r.gameType !== 'target' && <label>Accepted answers{q.answerType === 'output' ? ' (exact code/output)' : ' (one variant per line)'}<textarea className={q.answerType === 'output' ? 'code-answer' : ''} rows={4} value={q.answerType === 'output' ? q.acceptedAnswers[0] ?? '' : q.acceptedAnswers.join('\n')} onChange={e => patch({ acceptedAnswers: q.answerType === 'output' ? [e.target.value] : e.target.value.split('\n') })}/><small>{q.answerType === 'output' ? 'Case and internal spacing are preserved. Code is not executed.' : 'Case and extra whitespace are ignored. Add spelling variants explicitly.'}</small></label>}
          </fieldset>
          {preview && <QuestionPreview key={q.id} question={q} kind={r.gameType} images={images}/>}
        </>}
      </section></div>
    <footer className="content-footer"><p>Teams earn marks once per question. Scores update automatically when the question closes.</p><Button disabled={locked || busy} onClick={() => { setBusy(true); void contentService.bank(state.id).then(doc => { change(doc); setRound(0); setIndex(0) }).catch(e => setError(e.message)).finally(() => setBusy(false)) }}>Load v2 question bank</Button><Button onClick={() => void save()} busy={busy} disabled={locked || !dirty}>Save draft<Save size={18}/></Button></footer>
  </Page>
}

function withEntry(data: ContentQuestion['data'], field: 'cells' | 'clues', itemIndex: number, value: string): ContentQuestion['data'] {
  const list = (data[field] ?? []).map((entry, i) => i === itemIndex ? value : entry)
  return field === 'cells' ? { ...data, cells: list } : { ...data, clues: list }
}

function NumberList({ numbers, onChange }: { numbers: number[]; onChange: (numbers: number[]) => void }) {
  const [text, setText] = useState(numbers.join(', '))
  return <label>Available numbers (comma separated)<input value={text} onChange={e => { setText(e.target.value); onChange(e.target.value.split(',').filter(v => v.trim()).map(v => Number(v.trim()))) }}/></label>
}

function QuestionPreview({ question: q, kind, images }: { question: ContentQuestion; kind: string; images: Record<string, string> }) {
  const [start, setStart] = useState<number | null>(null), [now, setNow] = useState(Date.now()), [answer, setAnswer] = useState(''), [message, setMessage] = useState('')
  const [artist, setArtist] = useState(true), [strokes, setStrokes] = useState<import('../../types/game').DrawingStroke[]>([])
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 200); return () => clearInterval(timer) }, [])
  const prepTime = kind === 'memory' || kind === 'drawing' ? q.memoryTime ?? 10 : 0
  const elapsed = start === null ? 0 : Math.max(0, (now - start) / 1000), prep = elapsed < prepTime, ended = elapsed >= prepTime + (q.answerTime ?? 30)
  const data = { ...q.data, cells: q.data.cells?.map(c => images[c] ?? c), clues: q.data.clues?.map(c => images[c] ?? c).slice(0, Math.min(4, Math.floor(elapsed / 7) + 1)), secretCard: kind === 'drawing' && prep && artist ? q.prompt : undefined, isArtist: kind === 'drawing' && artist, strokes }
  const live: Question = { id: q.id, question: kind === 'drawing' ? 'Guess the drawing' : kind === 'memory' && prep ? 'Remember this grid' : q.prompt, questionType: q.answerType, gameType: kind, questionData: data, options: q.options, number: 1, durationSeconds: q.answerTime ?? 30, isDemo: q.isDemo, subphase: prep ? 'prepare' : 'answer' }
  return <section className="question-preview"><header><h3>Player preview</h3><span>{start === null ? 'Ready' : ended ? 'Question closed' : `${Math.ceil((prep ? prepTime : prepTime + (q.answerTime ?? 30)) - elapsed)} sec`}</span><button className="button secondary" onClick={() => { setStart(Date.now()); setAnswer(''); setMessage(''); setStrokes([]) }}>Restart preview</button>{kind === 'drawing' && <button className="button secondary" onClick={() => setArtist(v => !v)}>{artist ? 'View as teammate' : 'View as artist'}</button>}</header><p>This preview does not change the game or its scores. Secret cards are visible only in the artist’s view.</p><h3>{live.question}</h3><GameRenderer question={live} selected={answer} onSelect={setAnswer} disabled={ended} onStroke={async stroke => { setStrokes(old => [...old, stroke]) }}/>{!prep && !ended && !data.isArtist && <button className="button primary" disabled={!answer.trim()} onClick={() => setMessage('Preview answer received. No live marks were awarded.')}>Try answer</button>}{ended && <p>Answer: {kind === 'target' ? q.data.target : q.acceptedAnswers[0]}</p>}<p role="status">{message}</p></section>
}
