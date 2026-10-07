// Auth endpoints are intercepted. No emails sent or real passwords changed.
const { chromium } = require('playwright')
const { spawn } = require('node:child_process')
const path = require('node:path')
const assert = require('node:assert/strict')
let server, browser
const base = 'http://localhost:5176', userId = 'd39b6c7a-cf92-4a41-a158-ce9839547ad0'
const encode = value => Buffer.from(JSON.stringify(value)).toString('base64url')
const jwt = `${encode({alg:'HS256',typ:'JWT'})}.${encode({sub:userId,exp:Math.floor(Date.now()/1000)+3600,aud:'authenticated',role:'authenticated'})}.test-signature`
const user = {id:userId,email:'host@example.test',aud:'authenticated',role:'authenticated',app_metadata:{role:'host'},user_metadata:{},created_at:new Date().toISOString()}
let resetCalls = 0, updates = 0, nonHost = false, failRecovery = false, failUpdate = false
;(async()=>{
  server=spawn(process.execPath,[path.join(__dirname,'../node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','5176','--strictPort'],{cwd:path.join(__dirname,'..'),stdio:['ignore','pipe','pipe'],env:{...process.env,VITE_API_URL:'http://localhost:8004',VITE_DEMO:'false',VITE_SUPABASE_URL:'https://auth.example.test',VITE_SUPABASE_PUBLISHABLE_KEY:'',VITE_SUPABASE_ANON_KEY:'sb_publishable_ui_fixture'}})
  await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(new Error('Vite did not start')),20000);server.stdout.on('data',d=>{if(d.toString().includes(':5176/')){clearTimeout(timer);resolve()}});server.stderr.on('data',d=>console.error(d.toString()));server.on('exit',c=>{clearTimeout(timer);reject(new Error('Vite exited '+c))})})
  browser=await chromium.launch({headless:true})
  const context=await browser.newContext(), errors=[]
  await context.route('**/auth/v1/**',async route=>{
    const request=route.request(),url=new URL(request.url())
    if(url.pathname.endsWith('/recover')){
      assert.equal(request.postDataJSON().email,'host@example.test')
      assert.equal(url.searchParams.get('redirect_to'),base+'/control/reset-password')
      resetCalls++
      await route.fulfill({status:failRecovery?429:200,contentType:'application/json',body:JSON.stringify(failRecovery?{msg:'Please wait before requesting another link.'}:{})})
    }else if(url.pathname.endsWith('/user')&&request.method()==='PUT'){
      assert.equal(request.postDataJSON().password,'UiFixtureOnly!2468');updates++
      await route.fulfill({status:failUpdate?422:200,contentType:'application/json',body:JSON.stringify(failUpdate?{msg:'Password does not meet the configured policy.'}:user)})
    }else if(url.pathname.endsWith('/user'))await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(user)})
    else if(url.pathname.endsWith('/logout'))await route.fulfill({status:204,body:''})
    else await route.fulfill({status:200,contentType:'application/json',body:'{}'})
  })
  await context.route('**/api/**',async route=>{
    const authorized=Boolean(route.request().headers().authorization)&&!nonHost
    await route.fulfill({status:authorized?200:403,contentType:'application/json',body:JSON.stringify({success:authorized,data:authorized?{role:'host'}:null,error:authorized?null:{code:'UNAUTHORIZED_HOST'}})})
  })
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message))
  await page.goto(base+'/control');await page.getByRole('button',{name:'Forgot password?'}).waitFor()
  await page.getByRole('button',{name:'Forgot password?'}).click();await page.getByLabel('Email',{exact:true}).fill('host@example.test')
  await page.getByRole('button',{name:'Send reset link'}).click();await page.getByRole('status').filter({hasText:'If an account exists'}).waitFor();assert.equal(resetCalls,1)
  failRecovery=true;await page.getByRole('button',{name:'Send reset link'}).click();await page.getByRole('alert').filter({hasText:'Please wait'}).waitFor();failRecovery=false
  await page.getByRole('button',{name:'Back to host sign in'}).click();assert.equal(await page.getByLabel('Password',{exact:true}).inputValue(),'')
  await page.goto(base+'/control/reset-password');await page.getByRole('alert').filter({hasText:'missing or expired'}).waitFor();assert.equal(await page.getByRole('button',{name:'Save new password'}).count(),0)
  const recovery=base+'/control/reset-password#'+new URLSearchParams({access_token:jwt,refresh_token:'fixture-refresh',expires_in:'3600',token_type:'bearer',type:'recovery'})
  await page.goto(recovery);await page.getByLabel('New password',{exact:true}).waitFor()
  await page.getByLabel('New password',{exact:true}).fill('UiFixtureOnly!2468');await page.getByLabel('Confirm new password').fill('DifferentFixture!2468');await page.getByRole('button',{name:'Save new password'}).click();await page.getByRole('alert').filter({hasText:'do not match'}).waitFor();assert.equal(updates,0)
  await page.getByLabel('Confirm new password').fill('UiFixtureOnly!2468');failUpdate=true;await page.getByRole('button',{name:'Save new password'}).click();await page.getByRole('alert').filter({hasText:'configured policy'}).waitFor();failUpdate=false
  await page.getByLabel('Show passwords').check();assert.equal(await page.getByLabel('New password',{exact:true}).getAttribute('type'),'text')
  for(const width of [320,390,768]){await page.setViewportSize({width,height:900});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Password page overflow '+width)}
  await page.getByRole('button',{name:'Save new password'}).click();await page.getByRole('heading',{name:'Password updated'}).waitFor();await page.getByText('Your host email and account ID are unchanged. Sign in with your new password.').waitFor();assert.equal(updates,2)
  assert.equal(await page.getByLabel('New password',{exact:true}).count(),0)
  const stored=await page.evaluate(()=>Object.values(localStorage).join(' '));assert.ok(!stored.includes('UiFixtureOnly!2468'))
  await page.evaluate(()=>localStorage.clear());nonHost=true;await page.goto(recovery);await page.getByRole('alert').filter({hasText:'does not have permission'}).waitFor();assert.equal(await page.getByRole('button',{name:'Save new password'}).count(),0)
  assert.deepEqual(errors,[])
  console.log('Host auth UI passed: reset email request, rate limits, expired links, host authorization, confirmation, policy errors, same account update, cleared password fields and mobile widths. No live auth changes.')
})().catch(e=>{console.error(e);process.exitCode=1}).finally(async()=>{await browser?.close();server?.kill()})
