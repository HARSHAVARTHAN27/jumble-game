// Development-only empty foundation preview. No games, employees, or rounds are seeded.
import http from 'node:http'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const apiPort = Number(process.env.JUMBLE_DEMO_PORT || 8001)
const vitePort = process.env.JUMBLE_VITE_PORT || '5173'
const server = http.createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', req.headers.origin || 'http://localhost:5173')
  res.setHeader('Access-Control-Allow-Credentials', 'true')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization')
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return }
  const path = new URL(req.url, 'http://localhost').pathname
  const code = path.startsWith('/api/host/') ? 'UNAUTHORIZED_HOST' : 'NO_ACTIVE_GAME'
  res.writeHead(code === 'UNAUTHORIZED_HOST' ? 403 : 404, { 'Content-Type': 'application/json' })
  res.end(JSON.stringify({ success: false, data: null, error: { code } }))
})
server.listen(apiPort, '127.0.0.1', () => console.log('Empty foundation preview API ready'))
const vite = spawn(process.execPath, [resolve(root, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', vitePort, '--strictPort'], {
  cwd: root, stdio: 'inherit',
  env: { ...process.env, VITE_API_URL: `http://localhost:${apiPort}`, VITE_DEMO: 'true',
         VITE_SUPABASE_URL: '', VITE_SUPABASE_ANON_KEY: '' },
})
function close() { vite.kill(); server.close(); process.exit(0) }
process.on('SIGINT', close); process.on('SIGTERM', close); vite.on('exit', close)
