export const INTRO_DURATION = 4000
export const INTRO_STORAGE_KEY = 'jumble.splash.seen.v1'
export const INTRO_STAGES = [0, 500, 1200, 2000, 2500, 3000, 3500] as const

export function introSceneAt(elapsed: number) {
  let scene = 1
  INTRO_STAGES.forEach((start, index) => { if (elapsed >= start) scene = index + 1 })
  return scene
}
