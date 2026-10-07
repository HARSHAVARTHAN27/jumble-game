# Jumble frontend

React, Vite, TypeScript, Tailwind CSS, and Framer Motion. FastAPI owns database mutations and game rules.

```powershell
cd C:\Users\Harshavardhan\Desktop\Jumble\frontend
npm install
# Create .env from .env.example only if .env does not already exist.
npm run dev
```

Open http://localhost:5173. Configure VITE_API_URL for FastAPI and VITE_SUPABASE_URL / VITE_SUPABASE_PUBLISHABLE_KEY (or the legacy VITE_SUPABASE_ANON_KEY) with public browser credentials. Never use a backend secret/service-role key. The public Supabase client is shared by Auth and Realtime.

Player routes: /, /play, /login (same entry form), /lobby, /game, /results.

Host sign-in: /control. The /host entry URL redirects to /control and uses the same verified host access guard.
Control routes: /control, /control/content, /control/lobby, /control/game, /control/results.
The landing page has only Join Game. Each control route verifies host access through FastAPI before rendering host controls. Sign-in uses Supabase Auth; a UUID/localStorage entry cannot authorize a host.


Follow **backend/README.md** for database/import and host provisioning. The supplied 44-person CSV roster is imported into Supabase. Players enter their full name or employee ID, such as Harshavarthan or GIPL042, and go directly to /lobby. Duplicate full names require their ID for disambiguation. Teams and counts come from the database; there is no team selector or extra confirmation step. A signed HttpOnly cookie protects restoration; localStorage holds display IDs only.

When no game is active, verified employees still see their assigned team and wait in the lobby. They are enrolled automatically when the host opens a game. The waiting identity survives refresh; repeated enrollment does not duplicate the player count.

The host content editor supports Memory Grid, Emoji Decode, Connection Hunt, Target Drop, Draw & Guess and Technical Showdown. It saves drafts, uploads grid images, validates readiness and previews questions without awarding live marks. No actual question content is seeded. All questions have 30-second answer windows; memory/drawing have an additional 10-second preparation phase.

Authenticated FastAPI WebSockets deliver current gameplay snapshots, private artist cards and team drawings. Host sees drawing cards; guessers never receive them. Timers close questions and update host/player team scorecards automatically. REST polling and focus/reconnect restore snapshots. No sensitive database table is subscribed directly.

```powershell
npm run build
npm test
npm run test:browser
npm run test:gameplay
```

Browser checks use intercepted API fixtures and an isolated Vite process on port 5174. They verify name/ID entry, direct lobby navigation, waiting before game creation, automatic enrollment, denied control routes, restoration, and responsive widths. They do not write to Supabase.

Optional `npm run demo` starts an **empty foundation preview** on API port 8001. It contains no sample employees, games, rounds, questions, or authorized host access.

Apply backend/sql/gameplay.sql, configure public Auth credentials, provision the host and add real content. See ../GAMEPLAY.md for setup and play instructions. Browser checks use intercepted fixtures and never modify Supabase.

The redesigned lobby displays joined names by team and in a searchable participant list, with team filters, a YOU badge, and accessible new-arrival notices. Names refresh on the existing five-second poll, including while waiting for the host to create a game. Public game endpoints do not expose the roster.

