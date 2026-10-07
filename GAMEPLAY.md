# Jumble: host setup and six-round play

New games now load the complete supplied v2 question bank, with one demo and six scored questions per round. See [QUESTION_BANK.md](QUESTION_BANK.md) for the bank's timing, scoring, assets and full rehearsal instructions. The generic authoring rules below describe legacy/custom content; imported bank questions use their stored per-question settings.

## Activate the database

The backend now applies pending database migrations automatically on startup:

1. Add `DATABASE_URL` to `backend/.env` using the matching Supabase project's PostgreSQL direct or session-pooler connection string. Keep `AUTO_MIGRATE=true` (the default). See `backend/README.md` for the one-time setup.
2. Install `backend/requirements.txt` and start the backend. It applies the foundation and gameplay migrations before serving the app; existing data is retained and later starts skip completed migrations.
3. Start the frontend. Browser configuration must contain only the public Supabase key; never put the database connection string in Vite.
4. Run `python scripts/verify_gameplay.py` from `backend` to check the tables and image bucket without modifying data.

Manual SQL Editor setup remains available with `AUTO_MIGRATE=false`; see the backend README. Host accounts and employee imports remain separate from schema setup.

`jumble_content` stores ordered rounds, questions, answer variants and private asset paths. `jumble_runtime` stores the immutable live question definitions, phase timestamps, submissions, artist assignments, drawings and team scores. PostgreSQL functions lock the game and compare document versions, so saving/start and simultaneous answer/scoring writes remain atomic. Direct anonymous/authenticated reads and writes are denied; FastAPI uses its existing privileged client.

## Host login and content

Create the host in Supabase **Authentication → Users** and assign administrator-managed `app_metadata.role = "host"` using the SQL in `backend/README.md`, or run `python scripts/create_host.py --email host@example.com` from `backend` to do both steps and verify the password sign-in. Sign in at **http://localhost:5173/control** using that account's email/password.

Choose **Create Game**, which opens **Game Content**. Add at least one question to each of the six round forms. Save drafts and use Preview to rehearse. Grid cells support text/emojis/numbers or PNG/JPEG/WebP uploads up to 5 MB. File imports are not part of this version. Content is locked after starting.

**Create Game** always creates a fresh lobby. Any previous active session ends,
retaining its questions, submissions, memberships and earned scores. Unfinished
questions receive no extra marks. Previous players see **This session has ended**
and **Join New Game** when a new lobby is open; they re-enter their name or employee
ID to join with zero scores. **Play Again** separately copies completed-game content.

Choose **Open lobby**. Unsaved edits are saved before opening it. At least two players from each team must join, and all six rounds must validate, before **Let's Play** is enabled. Players join by their existing name or employee ID and retain their assigned teams.

## Timing and marks

Every question has a **30-second answer window**. Memory Grid and Draw & Guess also have a **10-second preparation phase** before that window. The host starts each question; the server closes it automatically at its deadline. The host can also end early. All players can retry, at most twice a second and 100 attempts per question. A team receives points only once.

| Round | Team marks per question |
|---|---|
| Memory Grid | First correct answer: 20; within 5 answering seconds: +5. |
| Emoji Decode | First correct answer: 20; first correct team: +10. |
| Connection Hunt | Clues appear at 0/7/14/21 seconds; correct answer earns 40/30/20/10. |
| Target Drop | Best valid result: exact 40; distance 1: 30; 2–3: 20; 4–5: 10; otherwise 0. |
| Draw & Guess | First correct teammate guess within 15 seconds: 30; after 15 and before the 30-second deadline: 20. |
| Technical Showdown | First correct answer: 30; first correct team: +10. Optional final hard question: 50 base, plus the same first-team bonus. |

Wrong/unanswered questions earn zero. For correctness-based rounds, the first correct answer locks the team; Target Drop keeps accepting improved results. Server receipt time and persisted sequence break ties. At the deadline, new answers are rejected.

Target Drop permits only +, −, ×, ÷ and parentheses, using each supplied number at most once (duplicates in the supplied list can each be used). A subset is allowed. Intermediate fractions are allowed, but the final result must be an integer. Arbitrary code is never executed.

Text grading ignores case and extra whitespace and uses host-entered accepted variants. Code/output preserves case and internal spacing, normalizing line endings and outer whitespace. After closing, the host may review text/output submissions; corrections recompute team marks and first-team bonuses from the original receipts and update both scorecards immediately. Advance only after finishing review.

## Draw & Guess privacy

One artist is selected randomly per team without repeating until available players have each drawn. Only the assigned artist and authorized host receive the secret card. The artist sees it for 10 seconds, then draws; teammates see their team's canvas and submit guesses. Other teams never receive the canvas. The host sees every canvas and keeps access to the card.

The host can reassign an artist if needed, keeping the original deadline. The replacement gets up to 10 seconds of card visibility within the remaining question time. Anyone who has seen that card as artist cannot guess it; reassignment must leave at least one eligible guesser. Strokes persist for reconnect recovery. A question allows up to 500 strokes per team with pen/eraser controls.

## Scores, recovery and deployment

After each question closes, host and players see each team's marks for that question and its cumulative total. Duplicate scoring calls do not add points twice. The scoring player's contribution is recorded once. The host advances to the next question/round; the game finishes only after the last technical question. Play Again creates a new lobby with copied content and fresh scores; players rejoin the new game.

Run one backend worker for this version. Use HTTPS and frontend/API on the same site in production, because player REST and WebSocket access use a signed HttpOnly cookie. Configure `FRONTEND_URL` to the exact frontend origin; WebSocket Origin checks reject others. Server timestamps recover timers after reconnect/restart, and a background worker closes expired questions even when browsers are closed. PostgreSQL CAS writes protect simultaneous updates. Production capacity/load testing has not been performed.

## Verification

Backend: `python -m pytest -q`. Frontend: `npm test`, `npm run build`, `npm run test:browser`, `npm run test:gameplay`. Tests use local database/API fixtures and do not write to Supabase. Browser screenshots appear under `frontend/test-artifacts`.
