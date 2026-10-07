# Jumble question bank v2

The existing React, FastAPI, Supabase content/runtime tables and WebSocket flow now use the supplied 42-challenge bank: one unscored demo followed by six scored questions in each round. The existing UI, teams and authentication remain intact.

## Content and assets

Private questions, accepted answers, independent clues, exact MCQ choices, code snippets, timings and scoring settings live in `backend/app/data/question_bank_v2.json`. `backend/app/services/question_bank.py` loads and validates that server-only file. It is never imported into the browser bundle.

The 14 updated DOCX visuals are in `frontend/public/images/questions/memory-demo.png` through `memory-q6.png`, and `emoji-demo.png` through `emoji-q6.png`. These use embedded images 43–56, superseding the old random emoji puzzles in images 1–14. Drawing cards and answer-bearing source cards are not public assets. Connection clues and technical content are transcribed into structured fields so clues reveal independently and code/options render separately.

Re-extract from the original DOCX by running `python backend/scripts/import_question_bank.py "C:\Users\Harshavardhan\Downloads\Jumble_Game_Question_Bank_v2.docx"` from the repository root. This script extracts assets and generates JSON; it does not access Supabase.

## Starting a full test game

1. Start the backend as described in `backend/README.md`, and run `npm run dev` in `frontend`.
2. Sign in at `/control` using your existing host account, then choose Create Game. New games without saved content load the v2 bank automatically.
3. For an existing lobby or draft, open Game Content, choose **Load v2 question bank**, then **Save draft**. Loading replaces only the editor draft; saving uses the existing version-checked content API. A running game remains locked.
4. Open the lobby. Join with existing employee names or IDs in separate browser sessions; each of the three existing teams needs at least two players.
5. Choose **Let's Play**, then **Start Demo**. Complete practice, choose **Continue · Start Round**, and start Q1. Continue through Q6, choose **End Round · Round Results**, and start the next round. Finish after Technical Showdown Q6.

Content is saved in the existing private `jumble_content.document` JSON and frozen in `jumble_runtime.state` at game start. No SQL migration, external seed operation, new table or replacement architecture is required. Existing saved drafts are retained until the host loads and saves the bank. Restart the backend after changing the source files. No live database was changed during automated verification.

## Validation and scoring

| Round | Server validation and bank rules |
|---|---|
| Memory Grid | Visual only during memorization; prompt and options hidden until then. Memorization: demo 10s, Q1–Q3 12s, Q4–Q5 15s, Q6 18s. One team answer; normalized text must match an accepted complete answer. 20 points; optional fastest bonus disabled. Answer window retains the existing 30s because the bank only specifies memorization time. |
| Emoji Decode | Updated clue image; case/whitespace-normalized text with explicit aliases. 20s; 20 points plus 10 for the first correct team. |
| Connection Hunt | Four separate clues; automatic reveal at 0/7/14/21s with host next-clue control. Server records the visible clue number; 40/30/20/10 points. Existing retry rule retained; a wrong guess does not lock the team. |
| Target Drop | Restricted arithmetic AST and exact rational arithmetic, no eval. All supplied numbers exactly once, only configured operators, final result an integer. Any valid expression accepted; example solution stays private until closure. 45s; exact teams earn 40. If no team is exact, valid teams rank by best distance for 30/20/10. Equal distances use original receipt order. |
| Draw & Guess | Random artist per team, rotation through eligible members before repeating. Card available only to artist during 10s preparation and host; teammates receive only their canvas. 45s guessing, 30/20/10 points at ≤15/≤30/≤45s; submissions are rejected at the deadline. |
| Technical Showdown | Exact selectable MCQ answer; one team submission, including wrong answers. Separate monospace code with original indentation. 20s, Q6 30s; 30 points plus first-team 10, Q6 50 base plus first-team 10. |

All demos accept attempts and reveal results but award exactly zero, with no score contribution or leaderboard change. Progress reads DEMO and QUESTION 1 / 6 through QUESTION 6 / 6. Authorized hosts see the answer and submissions while questions run; player payloads receive answers only after closure. Existing per-viewer WebSocket snapshots continue to propagate phases, clues, timers, drawings and scores.

## Changed source files

- Backend: `app/schemas/content.py`, `app/services/live_game.py`, `app/services/game_rules.py`, `app/routers/live.py`; new `app/services/question_bank.py`, `app/data/question_bank_v2.json`, `scripts/import_question_bank.py`, `tests/test_question_bank.py`; updated `tests/test_foundation.py` for seeded new-game behavior.
- Frontend: `src/types/content.ts`, `src/types/game.ts`, `src/services/normalize.ts`, `src/services/contentService.ts`, `src/components/game/GameRenderer.tsx`, `src/pages/PlayerGamePage.tsx`, `src/pages/host/GameContentPage.tsx`, `src/gameplay.css`, `scripts/gameplay-browser-check.cjs`; 14 new public question images.
- Documentation: this file and the bank note in `GAMEPLAY.md`; `.gitignore` excludes extraction QA images and pytest temporary directories.

## Verification and remaining setup

`backend/tests/test_question_bank.py` plays all 42 challenges through the actual persistent engine with an in-memory database boundary, checking privacy, phase timers, demo scoring, number/operator validation, artist rotation and all round transitions. The expanded browser gameplay check renders every imported question and verifies all 14 images, memory hiding, code indentation, mobile layout, demos and progress. Standard backend/frontend regression tests and the production build remain available.

Automated checks do not sign into or modify live Supabase. Real PostgreSQL integration checks need the existing optional `MIGRATION_TEST_DATABASE_URL` pointed at a disposable local database. A live event rehearsal still needs the host account, existing database setup, employee roster and separate player sessions; those are the site's existing setup requirements.

Final results: 109 backend tests passed; 13 optional PostgreSQL integration tests skipped. All 10 frontend unit tests passed. Production build passed with the existing large-bundle warning. The browser gameplay check passed, including all 42 bank challenges and all 14 updated visuals.
