// Foundation UI checks. API responses are intercepted test fixtures; no cloud writes.
const { chromium } = require('playwright')
const { randomUUID } = require('node:crypto')
const fs = require('node:fs')
const path = require('node:path')
const assert = require('node:assert/strict')
const { spawn } = require('node:child_process')
const baseURL = 'http://localhost:5174'
let testServer, browser
;(async () => {
  testServer = spawn(process.execPath, [path.join(__dirname, '../node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5174', '--strictPort'], {
    cwd: path.join(__dirname, '..'), stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env, VITE_API_URL: 'http://localhost:8002', VITE_DEMO: 'false', VITE_SUPABASE_URL: '', VITE_SUPABASE_ANON_KEY: '', VITE_SUPABASE_PUBLISHABLE_KEY: '' },
  })
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Verification server did not start')), 20000)
    testServer.stdout.on('data', chunk => { if (chunk.toString().includes(':5174/')) { clearTimeout(timer); resolve() } })
    testServer.stderr.on('data', chunk => console.error(chunk.toString()))
    testServer.on('exit', code => { clearTimeout(timer); reject(new Error('Verification server exited ' + code)) })
  })
  browser = await chromium.launch({ headless: true })
  const context = await browser.newContext()
  const errors = []
  const gameId = randomUUID(), playerId = randomUUID(), employeeId = randomUUID()
  const teams = ['Ctrl Alt Defeat', 'Titans', 'Vibe Tribe'].map((name, i) => ({ id: randomUUID(), name, joined: i === 0 ? 1 : 0, total: 1, score: 0 }))
  let joined = false, opened = false, friendJoined = false
  const player = () => ({ id: opened ? playerId : employeeId, name: 'Harshavarthan', gameId: opened ? gameId : '', waitingForGame: !opened, teamId: teams[0].id, score: 0, hasSubmitted: false })
  await context.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    let status = 200, data = null, code
    if (url.pathname.startsWith('/api/host/')) { status = 403; code = 'UNAUTHORIZED_HOST' }
    else if (url.pathname === '/api/player/join') {
      const body = route.request().postDataJSON()
      assert.equal('team_id' in body, false)
      if (!['harshavarthan', 'gipl042'].includes(body.name.trim().toLowerCase())) { status = 404; code = 'EMPLOYEE_NOT_FOUND' }
      else { joined = true; data = { player: player(), team: { id: teams[0].id, name: teams[0].name }, game: { id: opened ? gameId : '', status: opened ? 'lobby' : 'waiting' } } }
    } else if (joined) {
      if (url.pathname === '/api/game/active' && !opened) { status = 404; code = 'NO_ACTIVE_GAME' }
      else data = url.pathname === '/api/game/active' ? { id: gameId, status: 'lobby' } :
        { id: opened ? gameId : '', status: 'lobby', current_round: 0, total_rounds: 6, teams: teams.map((t, i) => ({ ...t, joined: i === 0 ? 1 : i === 1 && friendJoined ? 1 : 0 })), joined: friendJoined ? 2 : 1, total: 3, player: player(), participants: [{ id: employeeId, name: 'Harshavarthan', teamId: teams[0].id, isYou: true }, ...(friendJoined ? [{ id: 'friend', name: 'Kanishkaa', teamId: teams[1].id, isYou: false }] : [])] }
    } else { status = 404; code = 'NO_ACTIVE_GAME' }
    await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify({ success: !code, data, error: code ? { code } : null }) })
  })
  const page = await context.newPage()
  page.on('pageerror', error => errors.push(error.message))
  await page.goto(baseURL); await page.locator('.home-headline').waitFor()
  assert.equal(await page.getByRole('region', { name: 'Six game rounds' }).getByRole('listitem').count(), 6)
  await page.waitForFunction(() => [...document.querySelectorAll('.home-round-art img, .home-mascot')].length === 7 && [...document.querySelectorAll('.home-round-art img, .home-mascot')].every(image => image.complete && image.naturalWidth > 0))
  assert.equal(await page.getByRole('link', { name: 'Host Game', exact: true }).count(), 0)
  assert.equal(await page.locator('a[href^="/control"]').count(), 0)
  for (const width of [320, 390, 768, 1366, 1920]) {
    await page.setViewportSize({ width, height: 900 })
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'Landing overflow at ' + width)
  }
  fs.mkdirSync(path.join(__dirname, '../test-artifacts'), { recursive: true })
  await page.evaluate(() => document.fonts.ready)
  await page.setViewportSize({ width: 1672, height: 941 })
  await page.screenshot({ path: path.join(__dirname, '../test-artifacts/home-desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: path.join(__dirname, '../test-artifacts/home-mobile.png'), fullPage: true })
  await page.getByRole('link', { name: 'Join Game', exact: true }).click()
  await page.getByLabel('Your name or employee ID').waitFor()
  await page.goto(baseURL + '/control'); await page.getByRole('heading', { name: 'Restricted access' }).waitFor()
  assert.equal(await page.getByRole('button', { name: 'Create Game' }).count(), 0)
  await page.goto(baseURL + '/host')
  await page.getByRole('heading', { name: 'Restricted access' }).waitFor()
  assert.equal(new URL(page.url()).pathname, '/control')
  assert.equal(await page.getByRole('button', { name: 'Create Game' }).count(), 0)
  for (const route of ['/control/lobby', '/control/game', '/control/results']) {
    await page.goto(baseURL + route); await page.getByRole('heading', { name: 'Restricted access' }).waitFor()
    assert.equal(await page.locator('.host-controls, .host-lobby, .host-game').count(), 0)
  }
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto(baseURL + '/login')
  await page.getByLabel('Your name or employee ID').fill('Unknown')
  await page.getByRole('button', { name: 'Join Lobby' }).click()
  await page.getByRole('alert').waitFor()
  await page.getByLabel('Your name or employee ID').fill('gipl042')
  await page.getByRole('button', { name: 'Join Lobby' }).click()
  await page.locator('.player-lobby').waitFor()
  await page.getByText('Ctrl Alt Defeat', { exact: true }).first().waitFor()
  assert.equal(await page.locator('.host-controls, .lobby-start').count(), 0)
  await page.reload(); await page.locator('.player-lobby').waitFor()
  await page.locator('.lobby-player-details > summary').click()
  assert.equal(await page.getByRole('list', { name: 'Joined players' }).getByText('Harshavarthan', { exact: true }).count(), 1)
  await page.getByText('Waiting for the host to open the game.', { exact: true }).waitFor()
  assert.equal(await page.getByRole('button', { name: 'Join Team' }).count(), 0)
  friendJoined = true
  await page.getByRole('list', { name: 'Joined players' }).getByText('Kanishkaa', { exact: true }).waitFor({ timeout: 10000 })
  await page.getByRole('status').filter({ hasText: 'Kanishkaa joined the lobby.' }).waitFor({ state: 'attached' })
  await page.getByLabel('Search players').fill('kani')
  assert.equal(await page.locator('.crew-people li').count(), 1)
  await page.getByLabel('Search players').fill('no-match')
  await page.getByText('No players match that search.').waitFor()
  await page.getByLabel('Search players').fill('')
  await page.getByRole('button', { name: 'Titans 1', exact: true }).click()
  assert.equal(await page.locator('.crew-people li').count(), 1)
  await page.getByRole('button', { name: 'Everyone 2', exact: true }).click()
  opened = true
  await page.getByText('We’re waiting for more players to join…', { exact: true }).waitFor({ timeout: 10000 })
  await page.goto(baseURL + '/play')
  await page.getByLabel('Your name or employee ID').fill('  HARSHAVARTHAN  ')
  await page.getByRole('button', { name: 'Join Lobby' }).click()
  await page.locator('.player-lobby').waitFor()
  assert.equal(await page.locator('.lobby-your-team').count(), 1)
  assert.equal(await page.getByRole('region', { name: 'Ctrl Alt Defeat team' }).getByText('Your team', { exact: true }).count(), 1)
  await page.waitForFunction(() => [...document.querySelectorAll('.lobby-mascot')].length === 3 && [...document.querySelectorAll('.lobby-mascot')].every(image => image.complete && image.naturalWidth > 0))
  for (const width of [320, 390, 768, 1366, 1920]) {
    await page.setViewportSize({ width, height: 900 })
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'Lobby overflow at ' + width)
    if (width >= 1000) {
      assert.equal(await page.evaluate(() => document.documentElement.scrollHeight <= innerHeight), true, 'Lobby should fit screen height at ' + width)
      assert.equal(await page.locator('.illustrated-lobby').evaluate(element => element.getBoundingClientRect().width > innerWidth * .9), true, 'Lobby should fill screen width at ' + width)
    }
  }
  await page.setViewportSize({ width: 2556, height: 1307 })
  assert.equal(await page.evaluate(() => document.documentElement.scrollHeight <= innerHeight && document.documentElement.scrollWidth <= innerWidth), true, 'Lobby should fit the reference screen size')
  await page.setViewportSize({ width: 1366, height: 900 })
  await page.evaluate(() => document.fonts.ready)
  fs.mkdirSync(path.join(__dirname, '../test-artifacts'), { recursive: true })
  await page.screenshot({ path: path.join(__dirname, '../test-artifacts/foundation-player-lobby.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: path.join(__dirname, '../test-artifacts/lobby-mobile.png'), fullPage: true })
  await page.locator('.lobby-player-details > summary').focus()
  await page.keyboard.press('Enter')
  await page.getByLabel('Search players').waitFor()
  assert.deepEqual(errors, [])
  console.log('PASS: name and ID entry, direct lobby redirect, waiting before host opens, reload and automatic game enrollment, live joined names, arrival notices, search/team filters, protected control routes, five responsive widths; no browser errors.')
  await browser.close(); testServer.kill()
})().catch(async error => { console.error(error); await browser?.close(); testServer?.kill(); process.exitCode = 1 })



