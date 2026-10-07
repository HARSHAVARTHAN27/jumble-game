# JUMBLE splash storyboard

Final visual handoff: `jumble-splash-storyboard-v2.png`. Generated and refined with the built-in image-generation tool using the user's supplied storyboard as a visual reference. The original version is retained as `jumble-splash-storyboard.png`. This is a storyboard artifact, not a change to the running splash screen.

Four panels across the top, three wider panels below. Total animation: 4 seconds.

## Frontend implementation

The animated introduction is implemented in `frontend/src/components/intro/SplashIntro.tsx`
with the seven boundaries in `timeline.ts` and responsive materials/motion in
`frontend/src/splash.css`. It plays on first entry to `/`, `/play`, or `/login`,
then reveals that page after four seconds. It runs once per browser tab, tracked
in session storage; open a new tab to watch it again. Host, lobby, game and results
routes bypass the intro. Skip intro and Escape dismiss it immediately; users who
prefer reduced motion go straight to the page. No sound autoplays.

The app preloads beneath an inert, hidden layer so keyboard users cannot enter
the underlying page during the intro. Skipping by keyboard restores focus to the
page heading. Letter tiles, emblems and confetti are live HTML/CSS/SVG elements;
the edge artwork reuses the existing home page's brain, target and puzzle images.
No new backend endpoints or database changes are required for this animation.

Verification: `npm test`, `npm run build`, and `npm run test:splash` from `frontend`.

| Scene | Timing | Animation |
| --- | --- | --- |
| 1 | 0–0.5s | Trophy, target, lightning, brain and puzzle symbols rush inward from the edges; keep the center clear. |
| 2 | 0.5–1.2s | Six glossy J U M B L E tiles scatter around the center at different angles. |
| 3 | 1.2–2s | Tiles converge and snap into JUMBLE order, with curved motion paths. |
| 4 | 2–2.5s | Assembled logo lands with a small bounce and impact accents. |
| 5 | 2.5–3s | Fade in “6 Games. 3 Teams. 1 Winner.” beneath the logo. |
| 6 | 3–3.5s | Reveal “Get ready to think, react & compete.” and the three team emblems. |
| 7 | 3.5–4s | Controlled edge confetti; keep all copy legible before transitioning to Home / Join Game. |

Implementation color guide: the complete phrase “6 Games” is purple, “3 Teams” electric blue, and “1 Winner” orange. Keep those colors identical in scenes 5–7; generated lettering is a visual reference, so render final UI text with accessible HTML typography. Team emblems: Ctrl Alt Defeat / purple lightning; Titans / orange-red flame; Vibe Tribe / electric-blue sparkles. Preserve white space, soft lighting and restrained depth. No mascots or dark esports styling.

## Refinement prompt

Refine this existing JUMBLE storyboard image into the final polished professional UI animation handoff. Preserve exactly the seven-panel layout: four panels on the top row and three wider panels on the bottom. Preserve EVERY existing scene number, all timings and captions verbatim and legible. Preserve all scene contents, glossy 3D logo design, same letter colors, team emblem styling and names, white/light lavender backgrounds, fine panel borders. Make only these targeted improvements: In panels 5, 6 and 7 render the ENTIRE phrase "6 Games." in one consistent vivid purple, the ENTIRE phrase "3 Teams." in electric blue, and the ENTIRE phrase "1 Winner." in orange. No navy/black words mixed into the tagline. Use the same clean bold geometric sans-serif type styling for this tagline across all three panels. In panels 6 and 7 keep exact rally text "Get ready to think, react & compete." and labels "Ctrl Alt Defeat", "Titans", "Vibe Tribe" perfectly readable. Panel 1 needs more anticipation and negative space: move the game objects further to the outer edges so the center 60% is almost empty white; include trophy, target, lightning, brain and puzzle in the perimeter, with restrained smooth motion blur. Panel 7 should have fewer, deliberately placed confetti pieces, confined to the perimeter, so the central hero feels premium and uncluttered. Keep realistic soft lighting, crisp high-resolution output, glossy bevels and restrained shadows. Do not add characters, mascots, toys, dark esports backgrounds, new panels, or new text. Keep all timing captions and seven narrative beats intact.

## Generation prompt

Use case: ui-mockup. Create a high-resolution professional 7-panel animation storyboard for JUMBLE using the attached image as visual reference. Single landscape sheet, FOUR equal panels on TOP row, THREE wider panels on BOTTOM row. Exactly seven panels. Fine lavender panel borders and comfortable white gutters. Each panel visual above a small clean pale-lavender caption strip. Crisp typography, readable accurate English. Premium modern casual competitive team game for college students and office teams: white background, glossy beveled 3D letter tiles, purple electric blue orange subtle pink, soft realistic studio lighting/shadows, sophisticated and energetic. Consistent logo design across panels; no mascots, characters, preschool/toy look, rainbow clutter, dark esports, or cyberpunk.

Scene 1 (00:00–00:00.5): Almost empty white center. Trophy, target, lightning bolt, brain, puzzle piece and competitive symbols rush from outer edges with motion blur. Caption: "Scene 1" + timing + "Game elements rush in from the edges."
Scene 2 (00:00.5–00:01.2): Exactly six individual J U M B L E glossy tiles scattered around center, each at a different angle. Purple J and L, white U and E with black letters, blue M, orange B. Small confetti and motion trails. Caption: "Scene 2" + timing + "Six letter tiles appear, scattered and shuffled."
Scene 3 (00:01.2–00:02.0): Same tiles rearrange toward correct JUMBLE order, curved directional arrows, smooth trails. Caption: "Scene 3" + timing + "Letters move inward and snap into order."
Scene 4 (00:02.0–00:02.5): Large centered fully assembled JUMBLE, glossy 3D, tiny impact/bounce accent lines, immaculate white space. Caption: "Scene 4" + timing + "JUMBLE lands with a satisfying bounce."
Scene 5 (00:02.5–00:03.0): Same completed logo, tagline "6 Games. 3 Teams. 1 Winner." below. Entire phrase 6 Games purple, 3 Teams blue, 1 Winner orange. Soft outer-edge elements. Caption: "Scene 5" + timing + "The tagline fades in below the logo."
Scene 6 (00:03.0–00:03.5): Same logo/tagline. Below, exact text "Get ready to think, react & compete." Then three equally-spaced competitive team emblems horizontally: purple lightning with label "Ctrl Alt Defeat", orange/red flame with label "Titans", electric-blue star/sparkle with label "Vibe Tribe". Elegant embossed emblems, no cute faces. Caption: "Scene 6" + timing + "The rally line and three team emblems appear."
Scene 7 (00:03.5–00:04.0): Final hero composition with identical JUMBLE logo, tagline, rally line and all three labeled team emblems. Controlled confetti burst only at edges, central text perfectly readable. Caption: "Scene 7" + timing + "Edge confetti bursts; transition to Home / Join Game."

Bold geometric sans-serif, strong consistent hierarchy. All times must be accurate. Complete polished animation handoff sheet, not an implemented website. Output highest available resolution.
