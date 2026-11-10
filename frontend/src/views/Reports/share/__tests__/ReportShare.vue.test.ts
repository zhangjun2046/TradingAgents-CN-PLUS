import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ReportShare from '../../ReportShare.vue'

vi.mock('../useShareReport', async () => {
  const { ref } = await import('vue')
  return {
    useShareReport: () => ({
      loading: ref(false),
      error: ref(''),
      report: ref({
        stock_symbol: '00700',
        stock_name: '腾讯控股',
        analysis_date: '2026-11-02',
      }),
      departments: ref([]),
      activeDept: ref(undefined),
      activeRole: ref(undefined),
      showSubTabs: ref(false),
      location: ref({ tab: 'overview', role: '' }),
      selectTarget: vi.fn(),
      selectRole: vi.fn(),
      fetchSharedReport: vi.fn(),
    }),
  }
})

function setUserAgent(value: string): void {
  Object.defineProperty(navigator, 'userAgent', {
    configurable: true,
    get: () => value,
  })
}

async function mountShare(token = 'tok-1') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/s/:token', component: { template: '<div />' } }],
  })
  await router.push(`/s/${token}`)
  await router.isReady()
  const wrapper = mount(ReportShare, {
    global: {
      plugins: [router],
      stubs: {
        DeptTabs: true,
        OverviewPanel: true,
        RolePanel: true,
        IcpBeian: true,
      },
    },
  })
  return { wrapper, router }
}

describe('分享页导出弹层', () => {
  beforeEach(() => {
    setUserAgent('Mozilla/5.0 (iPhone) MicroMessenger/8.0.0')
  })

  it('微信内报告加载后不自动打开，点导出才出现引导', async () => {
    const { wrapper } = await mountShare()
    expect(wrapper.find('.export-layer').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('若直接下载受限')

    await wrapper.find('.export-open').trigger('click')

    expect(wrapper.find('.export-layer').exists()).toBe(true)
    expect(wrapper.text()).toContain('导出分析报告（免登录公开导出）')
    expect(wrapper.text()).toContain('若直接下载受限')
    expect(wrapper.text()).toContain('检测到当前为微信内置浏览器')
  })

  it('换一份报告时关闭已打开的导出弹层', async () => {
    const { wrapper, router } = await mountShare()
    await wrapper.find('.export-open').trigger('click')
    expect(wrapper.find('.export-layer').exists()).toBe(true)

    await router.push('/s/tok-2')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.export-layer').exists()).toBe(false)
  })
})
