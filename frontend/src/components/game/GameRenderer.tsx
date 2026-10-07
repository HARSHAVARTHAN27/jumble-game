import { motion } from 'framer-motion'
import { Check, Puzzle } from 'lucide-react'
import type { Question, DrawingStroke } from '../../types/game'
import { DrawingCanvas } from './DrawingCanvas'
import { useCountdown } from '../../hooks/useCountdown'
interface Props { question: Question; selected: string; onSelect: (answer: string) => void; disabled?: boolean; reveal?: boolean; host?: boolean; teamNames?: Record<string, string>; clockOffset?: number; onStroke?: (stroke: DrawingStroke) => Promise<void> }
export function MCQGame({ question, selected, onSelect, disabled, reveal }: Props) {
  return <div className="answer-options" role="radiogroup" aria-label="Answer choices">
    {question.options.map((answer, index) => {
      const correct = reveal && question.correctAnswer === answer
      return <motion.button type="button" role="radio" aria-checked={selected === answer} tabIndex={selected ? selected === answer ? 0 : -1 : index === 0 ? 0 : -1} key={answer} className={`answer-option ${selected === answer ? 'selected' : ''} ${correct ? 'correct-option' : ''}`} disabled={disabled} onClick={() => onSelect(answer)} onKeyDown={event => { if (!['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(event.key)) return; event.preventDefault(); const direction = event.key === 'ArrowDown' || event.key === 'ArrowRight' ? 1 : -1; const next = (index + direction + question.options.length) % question.options.length; onSelect(question.options[next]); (event.currentTarget.parentElement?.children[next] as HTMLButtonElement)?.focus() }} whileTap={{ scale: 0.985 }}><span className="option-letter">{String.fromCharCode(65 + index)}</span><span>{answer}</span>{(selected === answer || correct) && <Check size={22} aria-hidden="true"/>}</motion.button>
    })}
  </div>
}
export function GameRenderer(props: Props) {
  const { question: q, selected, onSelect, disabled, host, onStroke } = props
  const data = q.questionData ?? {}, prep = q.subphase === 'prepare'
  const cardRemaining = useCountdown(data.cardExpiresAt, 0, props.clockOffset ?? 0)
  const cardVisible = data.secretCard && (!data.cardExpiresAt || (cardRemaining !== null && cardRemaining > 0))
  const supported = ['memory', 'emoji', 'connection', 'target', 'drawing', 'technical', 'mcq'].includes(q.gameType)
  if (!supported) return <div className="unsupported"><Puzzle size={38}/><h3>Unsupported challenge</h3><p>Ask your host to check the content.</p></div>
  return <div className="round-interaction">
    {q.gameType === 'memory' && prep && (data.image ? <img className="bank-visual" src={data.image} alt="Workplace visual to memorize"/> : <div className="memory-grid" style={{ gridTemplateColumns: `repeat(${data.cols ?? 3}, minmax(0, 1fr))` }}>{data.cells?.map((cell, i) => <div key={i}>{/^https?:\/\//.test(cell) ? <img src={cell} alt={`Grid image ${i + 1}`}/> : <span>{cell}</span>}</div>)}</div>)}
    {q.gameType === 'emoji' && (data.image ? <img className="bank-visual" src={data.image} alt="Emoji concept clue"/> : <div className="emoji-puzzle">{data.puzzle}</div>)}
    {q.gameType === 'connection' && <ol className="connection-clues">{data.clues?.map((clue, i) => <li key={i}><span>Clue {i + 1}</span>{/^https?:\/\//.test(clue) ? <img src={clue} alt={`Clue ${i + 1}`}/> : <strong>{clue}</strong>}</li>)}</ol>}
    {q.gameType === 'target' && <div className="target-puzzle"><span>Target</span><strong>{data.target}</strong><div>{data.numbers?.map((n, i) => <span key={i}>{n}</span>)}</div><p>Use each number {data.useAllNumbers ? 'exactly' : 'at most'} once. {(data.operators ?? ['+', '-', '*', '/']).join(' ')} and parentheses are allowed.</p></div>}
    {q.gameType === 'technical' && data.code && <pre className="question-code"><code>{data.code}</code></pre>}
    {q.gameType === 'drawing' && <>
      {cardVisible && <div className="secret-card"><span>{host ? 'HOST ONLY · SECRET CARD' : 'YOUR SECRET CARD'}</span><strong>{data.secretCard}</strong><p>No speaking, actual word, letters, numbers, mouthing or spelling gestures. Do not show the secret card.</p></div>}
      {prep && !data.secretCard && <p className="prepare-note">Your artist is viewing the secret card. Guessing opens after preparation.</p>}
      {host ? Object.entries(data.canvases ?? {}).map(([teamId, strokes]) => <div key={teamId}><p>{props.teamNames?.[teamId] ?? 'Team'} · live canvas</p><DrawingCanvas strokes={strokes}/></div>) : <DrawingCanvas strokes={data.strokes ?? []} canDraw={Boolean(data.isArtist && !prep && !disabled)} onStroke={onStroke}/>}
      {data.isArtist && !prep && <p className="prepare-note">You’re the artist. Your teammates submit the guesses.</p>}
    </>}
    {!prep && !host && !data.isArtist && (q.questionType === 'mcq' ? <MCQGame {...props}/> : <label className="answer-input-label">{q.questionType === 'expression' ? 'Your expression' : q.questionType === 'output' ? 'Code / output answer' : 'Your answer'}<textarea className={`answer-input ${q.questionType === 'output' ? 'code-answer' : ''}`} value={selected} onChange={e => onSelect(e.target.value)} disabled={disabled} maxLength={q.questionType === 'expression' ? 200 : 4000} rows={q.questionType === 'output' ? 4 : 2} autoComplete="off" spellCheck={q.questionType !== 'output'}/></label>)}
    {!prep && host && q.questionType === 'mcq' && <MCQGame {...props} disabled/>}
  </div>
}
