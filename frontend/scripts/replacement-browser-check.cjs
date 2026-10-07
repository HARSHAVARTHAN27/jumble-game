// Local HTTP/WebSocket fixtures only; never contact Supabase or a live backend.
const { chromium } = require('playwright')
const { spawn } = require('node:child_process')
const path = require('node:path')
const fs = require('node:fs')
const assert = require('node:assert/strict')
const base = 'http://localhost:5177'
let server, browser, active = 'old-game', creates = 0, joins = 0, holdOld = false, releaseOld, oldHeld
const teams = ['Ctrl Alt Defeat', 'Titans', 'Vibe Tribe'].map((name,i) => ({id:'t'+i,name,joined:0,total:3,score:0}))
const snapshot = (id, player = false) => ({id, status:id==='old-game' && active!=='old-game'?'completed':'lobby',
  endedReason:id==='old-game' && active!=='old-game'?'replaced':null,newGameAvailable:id!==active,
  joined:player && id===active?1:0,total:9,current_round:0,teams,
  ...(player?{player:{id:id==='old-game'?'old-player':'new-player',name:'Player One',gameId:id,teamId:'t0',score:0,hasSubmitted:false}}:{})})
const ok = (route,data) => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({success:true,data,error:null})})
;(async()=>{
  server = spawn(process.execPath,[path.join(__dirname,'../node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','5177','--strictPort'],{cwd:path.join(__dirname,'..'),windowsHide:true,stdio:['ignore','pipe','pipe'],env:{...process.env,VITE_API_URL:'http://localhost:8004',VITE_DEMO:'false',VITE_SUPABASE_URL:'',VITE_SUPABASE_ANON_KEY:'',VITE_SUPABASE_PUBLISHABLE_KEY:''}})
  await new Promise((resolve,reject)=>{const timeout=setTimeout(()=>reject(new Error('Vite did not start')),20000);server.stdout.on('data',d=>{if(d.toString().includes(':5177/')){clearTimeout(timeout);resolve()}});server.stderr.on('data',d=>process.stderr.write(d));server.on('exit',()=>reject(new Error('Vite exited')))})
  browser = await chromium.launch({headless:true})
  const context = await browser.newContext({reducedMotion:'reduce'})
  const errors=[]
  await context.routeWebSocket('**/api/**',()=>{})
  await context.route('**/api/**',async route=>{
    const url=new URL(route.request().url()),p=url.pathname
    if(p==='/api/host/access')return ok(route,{role:'host'})
    if(p==='/api/game/active')return ok(route,{id:active,status:'lobby'})
    if(p==='/api/host/status'){
      const data=snapshot(url.searchParams.get('game_id'))
      if(holdOld && data.id==='old-game'){holdOld=false;oldHeld();await new Promise(resolve=>{releaseOld=resolve})}
      return ok(route,data)
    }
    if(p==='/api/host/game/create'){creates++;await new Promise(resolve=>setTimeout(resolve,250));active='new-game';return ok(route,{id:active,status:'lobby'})}
    if(p==='/api/host/game/content')return ok(route,{version:0,rounds:['memory','emoji','connection','target','drawing','technical'].map(gameType=>({gameType,questions:[]}))})
    if(p==='/api/player/state')return ok(route,snapshot(url.searchParams.get('game_id'),true))
    if(p==='/api/player/join'){joins++;return ok(route,{player:{id:'new-player',name:'Player One'},game:{id:active,status:'lobby'},team:{id:'t0',name:teams[0].name}})}
    throw new Error('Unexpected request: '+p)
  })
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message))
  await page.goto(base+'/control')
  await page.getByRole('button',{name:'Create Game'}).waitFor()
  await page.waitForFunction(()=>localStorage.getItem('jumble.game')==='old-game')
  const held=new Promise(resolve=>{oldHeld=resolve});holdOld=true
  await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await held
  await page.getByRole('button',{name:'Create Game'}).evaluate(button=>{button.click();button.click()})
  await page.getByRole('heading',{name:'Build the challenge.'}).waitFor()
  releaseOld()
  await page.waitForLoadState('networkidle')
  assert.equal(creates,1)
  assert.equal(await page.evaluate(()=>localStorage.getItem('jumble.game')),'new-game')
  assert.equal(await page.getByText('Content is locked').count(),0)
  await page.evaluate(()=>localStorage.setItem('jumble.player',JSON.stringify({id:'old-player',gameId:'old-game',teamId:'t0',name:'Player One',score:80,hasSubmitted:false})))
  await page.goto(base+'/lobby')
  await page.getByRole('heading',{name:'This session has ended.'}).waitFor()
  assert.equal(joins,0)
  for(const width of [390,1366]){await page.setViewportSize({width,height:900});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Ended session overflow')}
  fs.mkdirSync(path.join(__dirname,'../test-artifacts'),{recursive:true})
  await page.screenshot({path:path.join(__dirname,'../test-artifacts/replaced-session.png'),fullPage:true})
  await page.getByRole('link',{name:'Join New Game'}).click()
  await page.getByLabel('Your name or employee ID').fill('Player One')
  await page.getByRole('button',{name:'Join Lobby'}).click()
  await page.getByRole('heading',{name:'The crew is coming together.'}).waitFor()
  assert.equal(joins,1)
  const player=await page.evaluate(()=>JSON.parse(localStorage.getItem('jumble.player')))
  assert.equal(player.gameId,'new-game');assert.equal(player.score,0);assert.equal(player.teamId,'t0')
  assert.deepEqual(errors,[])
  console.log('Replacement UI passed: single creation on double-click, delayed old response ignored, fresh editor, ended-session notice, explicit rejoin, zero scores, mobile layout.')
})().catch(e=>{console.error(e);process.exitCode=1}).finally(async()=>{releaseOld?.();await browser?.close();server?.kill()})
