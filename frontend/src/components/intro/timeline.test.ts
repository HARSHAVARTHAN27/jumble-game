import { describe, expect, it } from 'vitest'
import { INTRO_DURATION, INTRO_STAGES, introSceneAt } from './timeline'

describe('four-second splash storyboard', () => {
  it('uses every storyboard boundary exactly once', () => {
    expect(INTRO_STAGES).toEqual([0,500,1200,2000,2500,3000,3500])
    INTRO_STAGES.forEach((time,index) => {
      expect(introSceneAt(time)).toBe(index+1)
      if (index) expect(introSceneAt(time-1)).toBe(index)
    })
    expect(INTRO_DURATION).toBe(4000)
    expect(introSceneAt(INTRO_DURATION)).toBe(7)
  })
})
