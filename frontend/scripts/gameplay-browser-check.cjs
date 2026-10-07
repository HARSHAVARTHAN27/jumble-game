// End-to-end UI fixtures only. No Supabase writes or real host login.
const { chromium } = require('playwright')
const { spawn } = require('node:child_process')
const path = require('node:path')
const fs = require('node:fs')
const assert = require('node:assert/strict')
let server, browser
const base = 'http://localhost:5175'
const types = ['memory','emoji','connection','target','drawing','technical']
const names = ['Memory Grid','Emoji Decode','Connection Hunt','Target Drop','Draw & Guess','Technical Showdown']
const bank = JSON.parse(fs.readFileSync(path.join(__dirname, '../../backend/app/data/question_bank_v2.json'), 'utf8'))
let content = { version: 0, rounds: types.map(gameType => ({ gameType, questions: [] })) }
const teams = ['Ctrl Alt Defeat','Titans','Vibe Tribe'].map((name,i) => ({ id: 't'+i,name,joined:2,total:2,score:0,roundGain:0 }))
const participants = teams.flatMap(t => [0,1].map(i => ({ id:t.id+'p'+i,name:'Player '+t.id+i,teamId:t.id,isYou:false })))
let phase = 'lobby', round = 1, question = null, reviewSubmissions = [], strokeCount = 0
const snapshot = (player = false) => ({ id:'game-ui',phase,status:phase === 'lobby' ? 'lobby' : 'playing',round,roundId:String(round),roundName:names[round-1],joined:6,total:6,teams,participants,question,reviewSubmissions,serverTime:new Date().toISOString(),isLastQuestion:false,...(player ? {player:{id:'t0p0',name:'Player t00',gameId:'game-ui',teamId:'t0',score:0,hasSubmitted:false}}:{}) })
;(async () => {
  server = spawn(process.execPath,[path.join(__dirname,'../node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','5175','--strictPort'],{cwd:path.join(__dirname,'..'),stdio:['ignore','pipe','pipe'],env:{...process.env,VITE_API_URL:'http://localhost:8003',VITE_DEMO:'false',VITE_SUPABASE_URL:'',VITE_SUPABASE_ANON_KEY:''}})
  await new Promise((resolve,reject) => { const timeout=setTimeout(()=>reject(new Error('Vite did not start')),20000); server.stdout.on('data',d=>{if(d.toString().includes(':5175/')){clearTimeout(timeout);resolve()}});server.stderr.on('data',d=>console.error(d.toString()));server.on('exit',c=>{clearTimeout(timeout);reject(new Error('Vite exited '+c))}) })
  browser = await chromium.launch({headless:true})
  const context = await browser.newContext()
  const errors=[]
  await context.route('**/api/**',async route=>{
    const req=route.request(),url=new URL(req.url()), p=url.pathname
    let data={}
    if(p==='/api/host/access')data={role:'host'}
    else if(p==='/api/game/active')data={id:'game-ui',status:phase==='lobby'?'lobby':'playing'}
    else if(p==='/api/host/game/content' && req.method()==='GET')data=content
    else if(p==='/api/host/game/content/bank')data={...bank,version:content.version}
    else if(p==='/api/host/game/content' && req.method()==='PUT'){content={...req.postDataJSON(),version:content.version+1};data={...content,errors:content.rounds.flatMap((r,i)=>r.questions.length?[]:[{path:'rounds.'+i,message:'Add at least one question.'}])}}
    else if(p==='/api/host/game/content/validate')data={ready:content.rounds.every(r=>r.questions.length),errors:[]}
    else if(p==='/api/host/status'||p==='/api/host/lobby')data=snapshot()
    else if(p==='/api/player/state')data=snapshot(true)
    else if(p.endsWith('/stroke')){strokeCount++;const body=req.postDataJSON();assert.ok(body.points.length);question.questionData.strokes.push(body);data={ok:true}}
    else if(p.endsWith('/submit')){assert.ok(req.postDataJSON().requestId);data={answerLocked:false}}
    else if(p.includes('/game/review/')){teams[0].score=30;teams[0].roundGain=30;reviewSubmissions[0].correct=true;data={ok:true}}
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({success:true,data,error:null})})
  })
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));await page.emulateMedia({reducedMotion:'reduce'})
  await page.goto(base+'/control/content');await page.getByRole('heading',{name:'Build the challenge.'}).waitFor()
  for(let i=0;i<6;i++){
    await page.getByRole('navigation',{name:'Game rounds'}).getByRole('button').nth(i).click()
    await page.getByRole('button',{name:'Add question',exact:true}).first().click()
    await page.getByLabel(i===4?'Secret card (artist and host only)':'Question',{exact:true}).fill(i===4?'ROBOT':'Question '+i)
    if(i===0){for(let cell=1;cell<=9;cell++)await page.getByLabel('Cell '+cell,{exact:true}).fill(String(cell));await page.getByLabel('Answer choices (one per line)').fill('1\n2\n3\n4');await page.getByLabel('Correct choice').selectOption('1')}
    else if(i===1){await page.getByLabel('Emoji puzzle').fill('🕷️ + 👨');await page.getByLabel('Accepted answers (one variant per line)').fill('Spider-Man')}
    else if(i===2){for(let c=0;c<4;c++)await page.getByLabel(`Clue ${c+1} · ${c*7} seconds`).fill('Clue '+c);await page.getByLabel('Accepted answers (one variant per line)').fill('Apple')}
    else if(i===4)await page.getByLabel('Accepted answers (one variant per line)').fill('Robot')
    else if(i===5){await page.getByLabel('Answer format').selectOption('output');await page.getByLabel('Accepted answers (exact code/output)').fill('404');await page.getByLabel('Final hard question · 50 base marks').check()}
    await page.getByRole('button',{name:'Save draft',exact:true}).first().click();await page.getByText('Draft saved',{exact:true}).waitFor()
  }
  assert.equal(content.rounds.length,6);assert.ok(content.rounds.every(r=>r.questions.length===1));assert.equal(content.rounds[5].questions[0].hard,true)
  await page.getByRole('button',{name:'Preview',exact:true}).click();await page.getByRole('heading',{name:'Player preview'}).waitFor()
  for(const width of [390,768,1366]) {
    await page.setViewportSize({width,height:900})
    const overflow = await page.evaluate(()=>[...document.querySelectorAll('*')].filter(e=>e.getBoundingClientRect().right>innerWidth).map(e=>({tag:e.tagName,cls:e.className,right:e.getBoundingClientRect().right})).slice(0,12))
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Editor overflow '+width+' '+JSON.stringify(overflow))
  }
  fs.mkdirSync(path.join(__dirname,'../test-artifacts'),{recursive:true});await page.screenshot({path:path.join(__dirname,'../test-artifacts/game-content.png'),fullPage:true})
  await page.getByRole('link',{name:'Open lobby'}).click();await page.getByRole('button',{name:'Let’s Play'}).waitFor();await page.waitForFunction(()=>[...document.querySelectorAll('button')].some(b=>b.textContent.includes('Let’s Play')&&!b.disabled))
  phase='active';round=5;question={id:'draw-q',question:'Draw the secret card',questionType:'text',gameType:'drawing',number:1,durationSeconds:30,startedAt:new Date().toISOString(),subphase:'answer',questionData:{secretCard:'ROBOT',artists:{t0:'t0p0',t1:'t1p0',t2:'t2p0'},canvases:{t0:[],t1:[],t2:[]}}}
  await page.goto(base+'/control/game');await page.getByText('ROBOT',{exact:true}).waitFor();assert.equal(await page.locator('.drawing-canvas').count(),3)
  await page.screenshot({path:path.join(__dirname,'../test-artifacts/host-drawing.png'),fullPage:true})
  phase='score_revealed';round=2;teams[1].score=30;teams[1].roundGain=30;question={id:'emoji-q',question:'Decode',questionType:'text',gameType:'emoji',number:1,durationSeconds:30,correctAnswer:'Spider-Man',questionData:{}};reviewSubmissions=[{id:'sub',playerId:'t0p0',teamId:'t0',answer:'Spiderman',correct:false,elapsed:1}]
  await page.goto(base+'/control/game');await page.getByRole('heading',{name:'The marks are in.'}).waitFor();await page.getByRole('button',{name:'Accept answer'}).click();await page.getByRole('button',{name:'Mark incorrect'}).waitFor();assert.equal(await page.locator('.question-scorecards section').count(),3)
  await page.screenshot({path:path.join(__dirname,'../test-artifacts/question-scores.png'),fullPage:true})
  phase='active';round=5;question={id:'draw-q',question:'Draw the secret card',questionType:'text',gameType:'drawing',number:1,durationSeconds:30,startedAt:new Date().toISOString(),subphase:'answer',questionData:{isArtist:true,strokes:[]}}
  await page.addInitScript(()=>localStorage.setItem('jumble.player',JSON.stringify({id:'t0p0',name:'Player t00',gameId:'game-ui',teamId:'t0',score:0,hasSubmitted:false})))
  await page.goto(base+'/game');await page.getByText('You’re the artist. Your teammates submit the guesses.').waitFor();assert.equal(await page.getByText('ROBOT',{exact:true}).count(),0)
  const canvas=await page.locator('.drawing-canvas').boundingBox();await page.mouse.move(canvas.x+20,canvas.y+20);await page.mouse.down();await page.mouse.move(canvas.x+100,canvas.y+80,{steps:5});await page.mouse.up();await page.waitForFunction(()=>document.querySelectorAll('.drawing-canvas polyline').length>0);assert.ok(strokeCount>=1)
  question.questionData={isArtist:false,strokes:question.questionData.strokes};await page.reload();await page.getByLabel('Your answer',{exact:true}).waitFor();await page.getByLabel('Your answer',{exact:true}).fill('Robot');await page.getByRole('button',{name:'Submit answer'}).click();await page.getByRole('status').filter({hasText:'Answer received.'}).waitFor()
  for(const width of [320,390,768]){await page.setViewportSize({width,height:900});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Game overflow '+width)}
  // Load the actual private bank through the host API, then render all 42 player challenges.
  phase='lobby'; await page.goto(base+'/control/content')
  await page.getByRole('button',{name:'Load v2 question bank',exact:true}).first().click()
  await page.getByText('DEMO · 0 POINTS',{exact:true}).waitFor()
  await page.getByRole('button',{name:'Save draft',exact:true}).first().click()
  await page.getByText('Draft saved',{exact:true}).waitFor()
  assert.ok(content.rounds.every(r=>r.questions.length===7 && r.questions[0].isDemo))
  await page.setViewportSize({width:390,height:900})
  for(let ri=0;ri<6;ri++) for(let qi=0;qi<7;qi++) {
    const card=bank.rounds[ri].questions[qi], kind=types[ri]
    phase='active';round=ri+1
    const prep=kind==='memory'||kind==='drawing'
    const data=kind==='memory'?{image:card.data.image}:kind==='connection'?{clues:card.data.clues.slice(0,1)}:kind==='drawing'?{isArtist:false,strokes:[]}:({...card.data,exampleSolution:undefined})
    question={id:card.id,question:kind==='memory'?'Remember this visual':kind==='drawing'?'Draw the secret card':card.prompt,questionType:card.answerType,gameType:kind,number:qi,isDemo:qi===0,scoredCount:6,lockAfterAttempt:card.lockAfterAttempt,instructions:card.instructions,durationSeconds:prep?card.memoryTime:card.answerTime,startedAt:new Date().toISOString(),subphase:prep?'prepare':'answer',questionData:data,options:prep?[]:card.options}
    await page.goto(base+'/game')
    await page.getByRole('heading',{name:question.question,exact:true}).waitFor({timeout:10000}).catch(async e=>{console.error('Bank card',card.id,'URL',page.url(),await page.locator('body').innerText());throw e})
    assert.ok((await page.locator('.question-meta').innerText()).includes(qi===0?'DEMO':`QUESTION ${qi} / 6`))
    if(kind==='memory'||kind==='emoji') {
      await page.locator('.bank-visual').waitFor()
      await page.waitForFunction(()=>document.querySelector('.bank-visual')?.complete && document.querySelector('.bank-visual')?.naturalWidth>0)
      if(qi===6) await page.screenshot({path:path.join(__dirname,`../test-artifacts/bank-${kind}-q6.png`),fullPage:true})
    }
    if(kind==='memory') {
      assert.equal(await page.getByText(card.prompt,{exact:true}).count(),0)
      question={...question,question:card.prompt,subphase:'answer',durationSeconds:card.answerTime,questionData:{},startedAt:new Date().toISOString(),options:card.options}
      await page.reload();await page.getByRole('heading',{name:card.prompt,exact:true}).waitFor()
      assert.equal(await page.locator('.bank-visual').count(),0)
    }
    if(kind==='technical') {
      assert.equal(await page.getByRole('radio').count(),4)
      assert.equal(await page.getByText('One answer per team.',{exact:true}).count(),1)
      if(card.data.code) assert.equal(await page.locator('.question-code code').textContent(),card.data.code)
      if(qi===6) await page.screenshot({path:path.join(__dirname,'../test-artifacts/bank-technical-q6.png'),fullPage:true})
    }
    if(kind==='connection') assert.equal(await page.locator('.connection-clues li').count(),1)
    if(kind==='drawing') assert.equal(await page.getByText(card.prompt,{exact:true}).count(),0)
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Bank mobile overflow '+card.id)
    if(qi===0) {
      phase='score_revealed';question={...question,correctAnswer:kind==='target'?card.data.exampleSolution:card.acceptedAnswers[0]}
      await page.reload();await page.getByText('Practice complete · 0 points. Scores are unchanged.',{exact:true}).waitFor()
      assert.equal(await page.locator('.question-scorecards').count(),0)
    }
  }
  assert.deepEqual(errors,[])
  console.log('Gameplay UI checks passed: authoring, private drawing, grading, mobile widths, bank loading, all 42 challenges, updated images, memory hiding, code indentation, demos and 1–6 progress.')
})().catch(e=>{console.error(e);process.exitCode=1}).finally(async()=>{await browser?.close();server?.kill()})
