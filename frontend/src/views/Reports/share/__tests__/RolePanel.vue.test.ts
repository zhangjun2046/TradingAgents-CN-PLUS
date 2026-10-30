import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import RolePanel from '../RolePanel.vue'
import type { VisibleRole } from '../shareConfig'

/**
 * jsdom 没有布局引擎，offsetHeight 默认为 0，window.innerHeight 也由测试自行指定。
 * 这里通过 mock offsetHeight / innerHeight 驱动 RolePanel 的折叠阈值判断。
 */
function makeRole(overrides: Partial<VisibleRole> = {}): VisibleRole {
  return {
    key: 'market',
    name: '市场分析师',
    field: 'market_report',
    content: '建议买入。',
    showsStance: true,
    ...overrides,
  }
}

/** 设置某个 DOM 元素的 offsetHeight（jsdom 只读属性，用 Object.defineProperty 覆盖） */
function setHeight(el: HTMLElement, height: number): void {
  Object.defineProperty(el, 'offsetHeight', { configurable: true, value: height })
}

describe('RolePanel 长文折叠', () => {
  let innerHeightSpy: ReturnType<typeof vi.spyOn>
  let observerInstances: Array<{ cb: () => void }>

  beforeEach(() => {
    observerInstances = []
    // ResizeObserver 在 jsdom 不存在，mock 出来并记录回调
    vi.stubGlobal(
      'ResizeObserver',
      class {
        cb: () => void
        constructor(cb: () => void) {
          this.cb = cb
          observerInstances.push({ cb })
        }
        observe() {}
        unobserve() {}
        disconnect() {}
      }
    )
    innerHeightSpy = vi.spyOn(window, 'innerHeight', 'get').mockReturnValue(1000)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('非文本内容不折叠、渲染 JSON 块', async () => {
    const wrapper = mount(RolePanel, {
      props: { role: makeRole({ content: { a: 1 } }) },
    })
    await nextTick()
    expect(wrapper.find('.fold-btn').exists()).toBe(false)
    expect(wrapper.find('.json-block').exists()).toBe(true)
    expect(wrapper.find('.json-block').text()).toContain('"a": 1')
  })

  it('正文高度超过 60vh 时默认折叠并显示展开按钮', async () => {
    const long = `## 结论\n建议买入。\n\n${'很长的正文内容'.repeat(200)}`
    const wrapper = mount(RolePanel, {
      props: { role: makeRole({ content: long }) },
    })
    await nextTick()

    const content = wrapper.find('.role-body > div').element as HTMLElement
    setHeight(content, 800) // > 0.6 * 1000
    // 触发一次 ResizeObserver 回调让 measure 重算
    observerInstances.forEach((o) => o.cb())
    await nextTick()

    expect(wrapper.find('.role-body').classes()).toContain('is-collapsed')
    const btn = wrapper.find('.fold-btn')
    expect(btn.exists()).toBe(true)
    expect(btn.text()).toContain('展开阅读完整正文')
    expect(btn.attributes('aria-expanded')).toBe('false')
  })

  it('点击展开按钮收起/展开切换', async () => {
    const long = `## 结论\n建议买入。\n\n${'很长的正文内容'.repeat(200)}`
    const wrapper = mount(RolePanel, {
      props: { role: makeRole({ content: long }) },
    })
    await nextTick()

    const content = wrapper.find('.role-body > div').element as HTMLElement
    setHeight(content, 800)
    observerInstances.forEach((o) => o.cb())
    await nextTick()

    const btn = wrapper.find('.fold-btn')
    expect(wrapper.find('.role-body').classes()).toContain('is-collapsed')

    await btn.trigger('click')
    expect(wrapper.find('.role-body').classes()).not.toContain('is-collapsed')
    expect(btn.text()).toBe('收起')
    expect(btn.attributes('aria-expanded')).toBe('true')

    await btn.trigger('click')
    expect(wrapper.find('.role-body').classes()).toContain('is-collapsed')
    expect(btn.attributes('aria-expanded')).toBe('false')
  })

  it('正文高度不足 60vh 时不折叠、无展开按钮', async () => {
    const wrapper = mount(RolePanel, {
      props: { role: makeRole({ content: '建议买入。' }) },
    })
    await nextTick()

    const content = wrapper.find('.role-body > div').element as HTMLElement
    setHeight(content, 300) // < 0.6 * 1000
    observerInstances.forEach((o) => o.cb())
    await nextTick()

    expect(wrapper.find('.role-body').classes()).not.toContain('is-collapsed')
    expect(wrapper.find('.fold-btn').exists()).toBe(false)
  })
})