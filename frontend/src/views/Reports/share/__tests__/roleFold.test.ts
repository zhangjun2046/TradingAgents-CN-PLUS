import { describe, expect, it } from 'vitest'
import { FOLD_HEIGHT_RATIO, isFoldable } from '../roleFold'

describe('isFoldable', () => {
  it('正文高度超过 60vh 时折叠', () => {
    expect(isFoldable(601, 1000)).toBe(true)
  })

  it('正文高度恰好等于 60vh 时不折叠', () => {
    expect(isFoldable(600, 1000)).toBe(false)
    expect(isFoldable(480, 800)).toBe(false)
  })

  it('正文高度不足 60vh 时不折叠', () => {
    expect(isFoldable(300, 1000)).toBe(false)
  })

  it('阈值比例与样式里的 60vh 保持一致', () => {
    expect(FOLD_HEIGHT_RATIO).toBe(0.6)
  })
})